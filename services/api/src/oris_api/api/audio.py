"""Routes de capture audio (spec §58–59)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Header, Response, status

from oris_api.api.dependencies import ActorDep, SessionDep, SettingsDep, SinkDep
from oris_api.api.schemas import (
    AudioGapOut,
    AudioGapReport,
    AudioSessionOut,
    ChunkReceiptOut,
    ClientConfigOut,
)
from oris_api.services import audio, encounters

router = APIRouter(tags=["audio"])


@router.put(
    "/encounters/{encounter_id}/audio/chunks/{sequence}",
    response_model=ChunkReceiptOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Segment déjà reçu à l'identique"}},
)
def put_chunk(
    encounter_id: UUID,
    sequence: int,
    payload: Annotated[bytes, Body(media_type=audio.AUDIO_FORMAT)],
    content_type: Annotated[str, Header()],
    x_chunk_timestamp_ms: Annotated[int, Header()],
    x_chunk_checksum: Annotated[str, Header(min_length=64, max_length=64)],
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
    sink: SinkDep,
    response: Response,
) -> ChunkReceiptOut:
    """Idempotent : renvoyer le même segment est sans effet."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    receipt = audio.store_chunk(
        session,
        sink,
        settings,
        encounter,
        sequence,
        x_chunk_timestamp_ms,
        x_chunk_checksum,
        content_type,
        payload,
    )
    if receipt.status == "duplicate":
        response.status_code = status.HTTP_200_OK
    return ChunkReceiptOut(sequence=receipt.sequence, status=receipt.status)


@router.post("/encounters/{encounter_id}/audio/gaps", response_model=AudioSessionOut)
def report_gap(
    encounter_id: UUID, body: AudioGapReport, session: SessionDep, actor: ActorDep
) -> AudioSessionOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    audio.report_gap(session, actor, encounter, body.reason, body.duration_ms)
    return get_audio(encounter_id, session, actor)


@router.get("/encounters/{encounter_id}/audio", response_model=AudioSessionOut)
def get_audio(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> AudioSessionOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    audio_session = audio.require_session_row(session, encounter)
    rows = audio.chunk_rows(session, audio_session)
    result = audio.coverage(session, audio_session)
    last_row = rows[-1] if rows else None
    return AudioSessionOut(
        status=audio_session.status,
        audio_format=audio_session.audio_format,
        received_count=result.received_count,
        last_sequence=result.last_sequence,
        next_sequence=(result.last_sequence + 1) if result.last_sequence is not None else 0,
        next_timestamp_ms=(last_row.timestamp_ms + last_row.duration_ms) if last_row else 0,
        missing_sequences=result.missing_sequences,
        received_duration_ms=result.received_duration_ms,
        gaps=[AudioGapOut(duration_ms=gap.duration_ms) for gap in result.gaps],
        reported_gap_reasons=[gap["reason"] for gap in audio_session.reported_gaps],
        purge_status=audio_session.purge_status,
        finalized_at=audio_session.finalized_at,
        purged_at=audio_session.purged_at,
        last_received_at=last_row.received_at if last_row else None,
    )


@router.get("/config/client", response_model=ClientConfigOut)
def client_config(settings: SettingsDep) -> ClientConfigOut:
    return ClientConfigOut(
        environment=settings.app_env,
        audio_format=audio.AUDIO_FORMAT,
        sample_rate=16_000,
        chunk_duration_ms=2_000,
        max_chunk_bytes=settings.audio_max_chunk_bytes,
        max_session_minutes=settings.max_session_minutes,
        warn_session_minutes=settings.warn_session_minutes,
        patient_information_mode=settings.patient_information_mode,
        test_audio_source_enabled=settings.app_env in {"local", "test"},
    )
