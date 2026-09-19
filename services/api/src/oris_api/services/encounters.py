"""Cycle de vie d'une consultation et pipeline clinique (spec §25, §49)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.contracts import ClinicalEncounter
from oris_api.contracts.generated import ClinicalEncounterStatus
from oris_api.db.models import Encounter
from oris_api.domain.lifecycle import TransitionError, ensure_transition
from oris_api.domain.resolver import resolve
from oris_api.domain.speaker_roles import apply_roles
from oris_api.domain.types import AudioChunk, AudioGap
from oris_api.domain.warnings import compute_warnings
from oris_api.providers import ProviderSet
from oris_api.providers.base import (
    ExtractionUnavailable,
    TranscriptionUnavailable,
    rule_codes,
)
from oris_api.services import async_bridge, audio, audit, documents
from oris_api.services.audio_sink import AudioSink
from oris_api.services.clinical_store import replace_segments, save_version
from oris_api.services.errors import Conflict, NotFound
from oris_api.services.identity import Actor
from oris_api.services.patients import get_patient
from oris_api.synthetic.corpus import SYNTHETIC_PAYLOAD_PREFIX

logger = logging.getLogger("oris.pipeline")
LOCALE = "fr-FR"
ALREADY_PROCESSED = frozenset({"review", "validated", "exported", "archived"})


def get_encounter(session: Session, actor: Actor, encounter_id: UUID) -> Encounter:
    encounter = session.get(Encounter, encounter_id)
    if encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("ENCOUNTER_NOT_FOUND", str(encounter_id))
    return encounter


def list_encounters(
    session: Session,
    actor: Actor,
    status: str | None = None,
    patient_id: UUID | None = None,
) -> list[Encounter]:
    statement = select(Encounter).where(Encounter.organization_id == actor.organization_id)
    if status:
        statement = statement.where(Encounter.status == status)
    if patient_id:
        statement = statement.where(Encounter.patient_id == patient_id)
    return list(session.scalars(statement.order_by(Encounter.created_at.desc())))


def create_encounter(
    session: Session,
    actor: Actor,
    patient_id: UUID,
    synthetic_case_id: str | None = None,
) -> Encounter:
    get_patient(session, actor, patient_id)
    metadata: dict[str, object] = {}
    if synthetic_case_id:
        metadata["synthetic_case_id"] = synthetic_case_id
    encounter = Encounter(
        organization_id=actor.organization_id,
        patient_id=patient_id,
        practitioner_id=actor.user_id,
        status="draft",
        mode="consultation",
        object_version=1,
        metadata_json=metadata,
    )
    session.add(encounter)
    session.flush()
    audit.record(session, actor, "encounter.created", "encounter", encounter.id)
    return encounter


def transition(
    session: Session, actor: Actor | None, encounter: Encounter, target: ClinicalEncounterStatus
) -> None:
    try:
        ensure_transition(encounter.status, target)
    except TransitionError as error:
        raise Conflict(
            "INVALID_TRANSITION", str(encounter.id), [error.current, error.target]
        ) from error
    previous = encounter.status
    encounter.status = target
    now = datetime.now(UTC)
    if target == "recording" and encounter.started_at is None:
        encounter.started_at = now
    if target == "finalizing":
        encounter.ended_at = now
    audit.record(
        session,
        actor,
        "encounter.status_changed",
        "encounter",
        encounter.id,
        previous=previous,
        current=target,
    )
    session.flush()


def is_synthetic(encounter: Encounter) -> bool:
    return isinstance(encounter.metadata_json.get("synthetic_case_id"), str)


def audio_input(
    session: Session, sink: AudioSink, encounter: Encounter
) -> tuple[list[AudioChunk], list[AudioGap]]:
    """Consultation fictive : charge synthétique. Sinon : segments captés et trous connus."""
    case_id = encounter.metadata_json.get("synthetic_case_id")
    if not isinstance(case_id, str):
        return audio.load_for_transcription(session, sink, encounter)
    payload = SYNTHETIC_PAYLOAD_PREFIX + case_id.encode()
    return [
        AudioChunk(
            session_id=str(encounter.id),
            sequence=0,
            timestamp_ms=0,
            checksum=hashlib.sha256(payload).hexdigest(),
            payload=payload,
        )
    ], []


def set_processing_errors(encounter: Encounter, errors: list[dict[str, str]]) -> None:
    metadata = dict(encounter.metadata_json)
    if errors:
        metadata["processing_errors"] = errors
    else:
        metadata.pop("processing_errors", None)
    encounter.metadata_json = metadata


def process(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    providers: ProviderSet,
    sink: AudioSink,
) -> Encounter:
    """Transcript → faits → résolveur → objet v1 → documents. Rejouable sans doublon."""
    if encounter.status in ALREADY_PROCESSED:
        return encounter
    transition(session, actor, encounter, "processing")
    started = datetime.now(UTC)

    chunks, capture_gaps = audio_input(session, sink, encounter)
    # Vrai micro → fournisseur configuré ; consultation fictive → fournisseur factice.
    stt = (
        providers.synthetic_speech_to_text if is_synthetic(encounter) else providers.speech_to_text
    )
    try:
        transcription = async_bridge.run(lambda: stt.transcribe(chunks, LOCALE, []))
    except TranscriptionUnavailable as error:
        # Panne du fournisseur : l'audio est conservé pour relancer le traitement.
        set_processing_errors(encounter, [{"rule": "STT_UNAVAILABLE", "subject_id": error.code}])
        transition(session, actor, encounter, "transcription_failed")
        logger.warning(
            "pipeline.stt_unavailable",
            extra={
                "encounter_id": str(encounter.id),
                "provider": stt.info.name,
                "error_code": error.code,
            },
        )
        return encounter
    # D010 : l'audio est éphémère ; purgé dès que la transcription a abouti.
    audio.purge(session, sink, encounter)
    if transcription.speaker_labels:
        transcription = replace(
            transcription,
            segments=apply_roles(transcription.segments, transcription.speaker_labels),
        )
    if not transcription.segments:
        set_processing_errors(
            encounter, [{"rule": "NO_TRANSCRIPT", "subject_id": str(encounter.id)}]
        )
        transition(session, actor, encounter, "transcription_failed")
        logger.warning("pipeline.transcription_failed", extra={"encounter_id": str(encounter.id)})
        return encounter
    replace_segments(session, encounter.id, transcription.segments)

    try:
        extraction = async_bridge.run(
            lambda: providers.clinical_extraction.extract(transcription.segments, [])
        )
    except ExtractionUnavailable as error:
        # Panne du fournisseur ou sortie refusée après ses essais : la consultation
        # reste en échec explicite, avec ce qui a été refusé. Jamais de texte inventé.
        reasons = rule_codes(error.details) or (error.code,)
        set_processing_errors(
            encounter, [{"rule": rule, "subject_id": str(encounter.id)} for rule in reasons]
        )
        transition(session, actor, encounter, "generation_failed")
        logger.warning(
            "pipeline.extraction_unavailable",
            extra={"encounter_id": str(encounter.id), "error_code": error.code},
        )
        return encounter
    violations = resolve(
        extraction.facts,
        extraction.treatment_plan,
        extraction.procedures,
        transcription.segments,
        from_extraction=True,
    )
    if violations:
        # Sortie rejetée entière, jamais corrigée en silence.
        set_processing_errors(
            encounter, [{"rule": v.rule, "subject_id": v.subject_id} for v in violations]
        )
        transition(session, actor, encounter, "generation_failed")
        logger.warning(
            "pipeline.extraction_rejected",
            extra={"encounter_id": str(encounter.id), "error_code": violations[0].rule},
        )
        return encounter

    set_processing_errors(encounter, [])
    clinical_object = ClinicalEncounter(
        encounter_id=str(encounter.id),
        patient_id=str(encounter.patient_id),
        practitioner_id=str(encounter.practitioner_id),
        started_at=(encounter.started_at or encounter.created_at).isoformat(),
        ended_at=encounter.ended_at.isoformat() if encounter.ended_at else None,
        status="review",
        object_version=1,
        facts=extraction.facts,
        treatment_plan=extraction.treatment_plan,
        procedures=extraction.procedures,
        warnings=compute_warnings([*capture_gaps, *transcription.gaps], transcription.segments),
    )
    save_version(session, encounter, clinical_object, "extraction", created_by=None)
    documents.generate(session, encounter, clinical_object, providers)
    transition(session, actor, encounter, "review")
    logger.info(
        "pipeline.completed",
        extra={
            "encounter_id": str(encounter.id),
            "duration_ms": round((datetime.now(UTC) - started).total_seconds() * 1000, 1),
        },
    )
    return encounter


def start(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    settings: Settings,
    patient_informed: bool,
) -> Encounter:
    """Début de l'écoute. L'information du patient est une condition paramétrable (§65)."""
    if settings.patient_information_mode == "confirm" and not patient_informed:
        raise Conflict("PATIENT_INFORMATION_REQUIRED", str(encounter.id))
    transition(session, actor, encounter, "recording")
    audio.open_session(session, encounter)
    if patient_informed:
        encounter.metadata_json = {
            **encounter.metadata_json,
            "patient_informed_at": datetime.now(UTC).isoformat(),
        }
        audit.record(session, actor, "encounter.patient_informed", "encounter", encounter.id)
    session.flush()
    return encounter


def finish(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    providers: ProviderSet,
    sink: AudioSink,
    final_sequence: int | None = None,
    client_recorded_ms: int | None = None,
    accept_gaps: bool = False,
) -> Encounter:
    if encounter.status in {"finalizing", "transcription_failed", "generation_failed"}:
        return process(session, actor, encounter, providers, sink)  # reprise sans doublon
    if encounter.status not in {"recording", "paused"}:
        raise Conflict("INVALID_TRANSITION", str(encounter.id), [encounter.status, "finalizing"])
    audio.finalize(session, actor, encounter, final_sequence, client_recorded_ms, accept_gaps)
    transition(session, actor, encounter, "finalizing")
    return process(session, actor, encounter, providers, sink)


def validate_encounter(session: Session, actor: Actor, encounter: Encounter) -> Encounter:
    active = [
        d for d in documents.list_documents(session, encounter.id) if d.status != "superseded"
    ]
    if not active or any(d.status != "validated" for d in active):
        raise Conflict("DOCUMENTS_NOT_VALIDATED", str(encounter.id))
    transition(session, actor, encounter, "validated")
    return encounter
