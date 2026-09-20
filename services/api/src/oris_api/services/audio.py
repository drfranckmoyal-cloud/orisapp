"""Capture audio côté serveur : réception idempotente, couverture, purge (spec §13, §59, §69)."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.db.models import AudioChunkRow, AudioSession, Encounter
from oris_api.domain.audio_coverage import ChunkInfo, Coverage, ReportedGap, compute_coverage
from oris_api.domain.types import AudioChunk, AudioGap
from oris_api.services import audit
from oris_api.services.audio_sink import AudioSink
from oris_api.services.errors import Conflict, NotFound, Unprocessable
from oris_api.services.identity import Actor

logger = logging.getLogger("oris.audio")

AUDIO_FORMAT = "audio/pcm;rate=16000;channels=1;encoding=s16le"
BYTES_PER_MS = 32  # 16 000 échantillons/s × 2 octets / 1 000
CAPTURING = frozenset({"recording", "paused"})
# Consultations dont le son n'a plus lieu d'être : le traitement est passé (D010).
PROCESSED_STATUSES = frozenset({"review", "validated", "exported", "archived", "generation_failed"})
GapReason = Literal[
    "microphone_lost",
    "page_reloaded",
    "capture_error",
    "audio_interruption",
    "route_change",
    "app_terminated",
]


@dataclass(frozen=True)
class ChunkReceipt:
    sequence: int
    status: Literal["stored", "duplicate"]


def get_session_row(session: Session, encounter: Encounter) -> AudioSession | None:
    return session.scalar(select(AudioSession).where(AudioSession.encounter_id == encounter.id))


def require_session_row(session: Session, encounter: Encounter) -> AudioSession:
    row = get_session_row(session, encounter)
    if row is None:
        raise NotFound("AUDIO_SESSION_NOT_FOUND", str(encounter.id))
    return row


def open_session(session: Session, encounter: Encounter) -> AudioSession:
    row = get_session_row(session, encounter)
    if row is None:
        row = AudioSession(encounter_id=encounter.id, status="open", audio_format=AUDIO_FORMAT)
        session.add(row)
        session.flush()
    return row


def chunk_rows(session: Session, audio_session: AudioSession) -> list[AudioChunkRow]:
    return list(
        session.scalars(
            select(AudioChunkRow)
            .where(AudioChunkRow.audio_session_id == audio_session.id)
            .order_by(AudioChunkRow.sequence)
        )
    )


def store_chunk(
    session: Session,
    sink: AudioSink,
    settings: Settings,
    encounter: Encounter,
    sequence: int,
    timestamp_ms: int,
    checksum: str,
    content_type: str,
    payload: bytes,
) -> ChunkReceipt:
    if encounter.status not in CAPTURING:
        raise Conflict("ENCOUNTER_NOT_RECORDING", str(encounter.id), [encounter.status])
    audio_session = require_session_row(session, encounter)
    if content_type.replace(" ", "").lower() != AUDIO_FORMAT:
        raise Unprocessable("UNSUPPORTED_AUDIO_FORMAT", str(encounter.id))
    if sequence < 0 or timestamp_ms < 0:
        raise Unprocessable("INVALID_CHUNK", str(encounter.id))
    if not payload or len(payload) % 2:
        raise Unprocessable("INVALID_CHUNK", str(encounter.id))
    if len(payload) > settings.audio_max_chunk_bytes:
        raise Unprocessable("CHUNK_TOO_LARGE", str(encounter.id))
    digest = hashlib.sha256(payload).hexdigest()
    if digest != checksum.lower():
        raise Unprocessable("CHECKSUM_MISMATCH", str(encounter.id), [str(sequence)])

    existing = session.scalar(
        select(AudioChunkRow).where(
            AudioChunkRow.audio_session_id == audio_session.id,
            AudioChunkRow.sequence == sequence,
        )
    )
    if existing is not None:
        if existing.checksum != digest:
            raise Conflict("CHUNK_CONFLICT", str(encounter.id), [str(sequence)])
        if sink.load(audio_session.id, sequence) is None:
            sink.store(audio_session.id, sequence, payload)
        return ChunkReceipt(sequence, "duplicate")

    sink.store(audio_session.id, sequence, payload)
    try:
        with session.begin_nested():
            session.add(
                AudioChunkRow(
                    audio_session_id=audio_session.id,
                    sequence=sequence,
                    timestamp_ms=timestamp_ms,
                    duration_ms=max(1, round(len(payload) / BYTES_PER_MS)),
                    byte_size=len(payload),
                    checksum=digest,
                )
            )
    except IntegrityError as error:  # envoi concurrent du même segment
        raise Conflict("CHUNK_CONFLICT", str(encounter.id), [str(sequence)]) from error
    return ChunkReceipt(sequence, "stored")


def report_gap(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    reason: GapReason,
    duration_ms: int | None,
) -> AudioSession:
    if encounter.status not in CAPTURING:
        raise Conflict("ENCOUNTER_NOT_RECORDING", str(encounter.id), [encounter.status])
    audio_session = require_session_row(session, encounter)
    audio_session.reported_gaps = [
        *audio_session.reported_gaps,
        {"reason": reason, "duration_ms": duration_ms},
    ]
    audit.record(session, actor, "audio.gap_reported", "encounter", encounter.id, reason=reason)
    session.flush()
    return audio_session


def coverage(session: Session, audio_session: AudioSession) -> Coverage:
    return compute_coverage(
        [
            ChunkInfo(r.sequence, r.timestamp_ms, r.duration_ms)
            for r in chunk_rows(session, audio_session)
        ],
        final_sequence=audio_session.final_sequence,
        reported=[ReportedGap(g["reason"], g["duration_ms"]) for g in audio_session.reported_gaps],
    )


def finalize(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    final_sequence: int | None,
    client_recorded_ms: int | None,
    accept_gaps: bool,
) -> None:
    """Clôt la capture. Refuse s'il manque des segments, sauf perte assumée."""
    audio_session = get_session_row(session, encounter)
    if audio_session is None:
        return
    rows = chunk_rows(session, audio_session)
    last = rows[-1].sequence if rows else -1
    announced = last if final_sequence is None else final_sequence
    if announced < last:
        raise Unprocessable("FINAL_SEQUENCE_TOO_LOW", str(encounter.id))
    received = {r.sequence for r in rows}
    missing = [s for s in range(announced + 1) if s not in received]
    if missing and not accept_gaps:
        raise Conflict("AUDIO_CHUNKS_MISSING", str(encounter.id), [str(s) for s in missing[:50]])
    audio_session.final_sequence = announced
    audio_session.client_recorded_ms = client_recorded_ms
    audio_session.status = "finalized"
    audio_session.finalized_at = datetime.now(UTC)
    audit.record(session, actor, "audio.finalized", "encounter", encounter.id,
                 chunk_count=len(rows), missing_count=len(missing))  # fmt: skip
    session.flush()


def load_for_transcription(
    session: Session, sink: AudioSink, encounter: Encounter
) -> tuple[list[AudioChunk], list[AudioGap]]:
    """Segments reçus, dans l'ordre, et trous connus (manquants, discontinus, signalés)."""
    audio_session = get_session_row(session, encounter)
    if audio_session is None:
        return [], []
    result = coverage(session, audio_session)
    gaps = list(result.gaps)
    chunks: list[AudioChunk] = []
    if audio_session.purge_status == "purged":
        return chunks, gaps
    for row in chunk_rows(session, audio_session):
        payload = sink.load(audio_session.id, row.sequence)
        if payload is None:  # perdu côté stockage : jamais masqué
            gaps.append(AudioGap(after_segment_id=None, duration_ms=row.duration_ms))
            continue
        chunks.append(
            AudioChunk(
                session_id=str(audio_session.id),
                sequence=row.sequence,
                timestamp_ms=row.timestamp_ms,
                checksum=row.checksum,
                payload=payload,
            )
        )
    return chunks, gaps


def purge(session: Session, sink: AudioSink, encounter: Encounter) -> None:
    audio_session = get_session_row(session, encounter)
    if audio_session is None or audio_session.purge_status == "purged":
        return
    sink.purge(audio_session.id)
    audio_session.purge_status = "purged"
    audio_session.purged_at = datetime.now(UTC)
    audit.record(
        session,
        None,
        "audio.purged",
        "encounter",
        encounter.id,
        organization_id=encounter.organization_id,
    )
    session.flush()


@dataclass(frozen=True)
class PurgeReport:
    """Ce qu'une passe de purge a fait, et ce qu'elle n'a pas pu faire."""

    purged: list[UUID]
    failed: list[UUID]
    remaining: int


def purge_pending(
    session: Session, sink: AudioSink, statuses: Collection[str] = PROCESSED_STATUSES
) -> PurgeReport:
    """Purge le son des consultations déjà traitées (D010).

    Rejouable : une session déjà purgée est ignorée, un échec n'interrompt pas la passe
    et ressort dans le rapport. Observable : chaque purge laisse une trace d'audit.
    """
    rows = session.scalars(
        select(AudioSession)
        .join(Encounter, Encounter.id == AudioSession.encounter_id)
        .where(AudioSession.purge_status != "purged", Encounter.status.in_(statuses))
    )
    purged: list[UUID] = []
    failed: list[UUID] = []
    for row in rows:
        try:
            sink.purge(row.id)
        except Exception:
            failed.append(row.encounter_id)
            logger.warning("audio.purge_failed", extra={"encounter_id": str(row.encounter_id)})
            continue
        row.purge_status = "purged"
        row.purged_at = datetime.now(UTC)
        encounter = session.get(Encounter, row.encounter_id)
        audit.record(
            session,
            None,
            "audio.purged",
            "encounter",
            row.encounter_id,
            organization_id=encounter.organization_id if encounter else None,
            job="purge",
        )
        purged.append(row.encounter_id)
    session.flush()
    remaining = (
        session.scalar(
            select(func.count())
            .select_from(AudioSession)
            .join(Encounter, Encounter.id == AudioSession.encounter_id)
            .where(AudioSession.purge_status != "purged", Encounter.status.in_(statuses))
        )
        or 0
    )
    return PurgeReport(purged=purged, failed=failed, remaining=remaining)
