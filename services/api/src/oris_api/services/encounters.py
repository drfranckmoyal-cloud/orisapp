"""Cycle de vie d'une consultation et pipeline clinique (spec §25, §49)."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.contracts import ClinicalEncounter
from oris_api.contracts.generated import ClinicalEncounterStatus
from oris_api.db.models import (
    Encounter,
    EncounterMarkRow,
    EncounterObjectVersion,
    LearningEventRow,
)
from oris_api.domain.lifecycle import TransitionError, ensure_transition
from oris_api.domain.resolver import resolve
from oris_api.domain.speaker_roles import apply_roles
from oris_api.domain.types import AudioChunk, AudioGap, TranscriptionResult
from oris_api.domain.warnings import compute_warnings
from oris_api.llm.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from oris_api.providers import ProviderSet
from oris_api.providers.base import (
    ExtractionUnavailable,
    TranscriptionUnavailable,
    rule_codes,
)
from oris_api.services import async_bridge, audio, audit, documents, personalization, registry
from oris_api.services.audio_sink import AudioSink
from oris_api.services.clinical_store import (
    load_current,
    load_segments,
    replace_segments,
    save_version,
)
from oris_api.services.errors import Conflict, NotFound
from oris_api.services.identity import Actor
from oris_api.services.patients import get_patient
from oris_api.stt.audio import SEUIL_SILENCE, concatenate, est_une_note, niveau
from oris_api.synthetic.corpus import SYNTHETIC_PAYLOAD_PREFIX

logger = logging.getLogger("oris.pipeline")
LOCALE = "fr-FR"
ALREADY_PROCESSED = frozenset({"review", "validated", "exported", "archived"})
#: Un traitement sans nouvelles depuis ce délai a été coupé (Mac en veille…) : on reprend.
REPRISE_APRES = timedelta(minutes=5)


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


SHADOW_MODE = "shadow"


def is_shadow(encounter: Encounter) -> bool:
    """Mode ombre : Oris écrit en parallèle, le praticien ne s'en sert pas (M11).

    Sert à mesurer Oris en conditions réelles sans qu'aucune de ses sorties n'entre
    dans un dossier : un document d'ombre ne peut être ni validé ni exporté.
    """
    return encounter.mode == SHADOW_MODE


def create_encounter(
    session: Session,
    actor: Actor,
    patient_id: UUID,
    synthetic_case_id: str | None = None,
    shadow: bool = False,
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
        mode=SHADOW_MODE if shadow else "consultation",
        object_version=1,
        metadata_json=metadata,
    )
    session.add(encounter)
    session.flush()
    audit.record(
        session, actor, "encounter.created", "encounter", encounter.id, mode=encounter.mode
    )
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


#: Pendant l'écoute ou le traitement, un autre fil de travail écrit dans la consultation :
#: la supprimer sous ses pieds le ferait échouer à mi-chemin.
EN_COURS = frozenset({"recording", "paused", "finalizing", "processing"})


def delete_encounter(session: Session, actor: Actor, encounter: Encounter, sink: AudioSink) -> None:
    """Supprime une consultation et tout ce qu'Oris en a tiré.

    Partent avec elle : le son s'il en reste, la transcription, le dossier clinique, les
    documents et leurs envois, et les corrections qu'elle a apprises à Oris — elles citent
    son contenu. Restent : les pièces jointes, qui appartiennent au patient, et une ligne
    du journal d'audit qui dit qu'une consultation a été supprimée, sans rien en dire.
    """
    if encounter.status in EN_COURS:
        raise Conflict("ENCOUNTER_IN_PROGRESS", str(encounter.id), [encounter.status])
    audio_session = audio.get_session_row(session, encounter)
    if audio_session is not None:
        sink.purge(audio_session.id)
    session.execute(delete(LearningEventRow).where(LearningEventRow.encounter_id == encounter.id))
    audit.record(
        session,
        actor,
        "encounter.deleted",
        "encounter",
        encounter.id,
        patient_id=str(encounter.patient_id),
        status=encounter.status,
    )
    session.delete(encounter)
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
    # Reprise : un traitement coupé net (Mac en veille, serveur arrêté) laisse la
    # consultation « en traitement ». Si la transcription était déjà faite — le son est
    # alors effacé — on repart de là, au lieu de rester bloqué pour toujours.
    if encounter.status == "processing":
        # Un traitement en cours ne se relance pas : deux à la fois se marcheraient
        # dessus. Au-delà de cinq minutes sans fin, il a été coupé net : on reprend.
        commence = encounter.metadata_json.get("traitement_commence_le")
        if commence and datetime.now(UTC) - datetime.fromisoformat(commence) < REPRISE_APRES:
            raise Conflict("PROCESSING_IN_PROGRESS", str(encounter.id))
    encounter.metadata_json = {
        **encounter.metadata_json,
        "traitement_commence_le": datetime.now(UTC).isoformat(),
    }
    if encounter.status != "processing":
        transition(session, actor, encounter, "processing")
    elif session.scalar(
        select(EncounterObjectVersion.version)
        .where(EncounterObjectVersion.encounter_id == encounter.id)
        .limit(1)
    ):
        # Coupé plus tard encore : le dossier clinique était enregistré, seule la
        # rédaction des documents manquait. On la refait, rien d'autre.
        logger.info("pipeline.resumed", extra={"encounter_id": str(encounter.id)})
        documents.generate(session, encounter, load_current(session, encounter), providers)
        transition(session, actor, encounter, "review")
        return encounter
    started = datetime.now(UTC)

    # Dictionnaire du praticien : il aide la machine à entendre et à nommer ; il
    # n'ajoute jamais un fait (invariants d'apprentissage).
    hints = personalization.hints_for(session, encounter.practitioner_id)
    chunks, capture_gaps = audio_input(session, sink, encounter)
    segments_gardes = load_segments(session, encounter.id) if not chunks else []
    if segments_gardes:
        # La transcription a déjà abouti (son effacé, phrases rangées) : on la reprend.
        logger.info("pipeline.resumed", extra={"encounter_id": str(encounter.id)})
        transcription = TranscriptionResult(segments=segments_gardes)
    else:
        # Vrai micro → fournisseur configuré ; consultation fictive → fournisseur factice.
        stt = (
            providers.synthetic_speech_to_text
            if is_synthetic(encounter)
            else providers.speech_to_text
        )
        stt_model = registry.model_version(
            session, "speech_to_text", stt.info.name, stt.info.version
        )
        stt_timer = registry.start_run("speech_to_text", encounter.id)
        try:
            transcription = async_bridge.run(lambda: stt.transcribe(chunks, LOCALE, hints))
        except TranscriptionUnavailable as error:
            registry.finish_run(
                session,
                stt_timer,
                status="failed",
                error_code=error.code,
                model_version_id=stt_model.id,
                counters={"chunks": len(chunks)},
            )
            # Panne du fournisseur : l'audio est conservé pour relancer le traitement.
            set_processing_errors(
                encounter, [{"rule": "STT_UNAVAILABLE", "subject_id": error.code}]
            )
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
        # Le volume, mesuré avant la purge : un nombre, jamais le son.
        niveau_audio = (
            {"crete": 1.0, "moyen": 1.0} if is_synthetic(encounter) else niveau(concatenate(chunks))
        )
        encounter.metadata_json = {**encounter.metadata_json, "niveau_audio": niveau_audio}
        # D010 : l'audio est éphémère ; purgé dès que la transcription a abouti.
        audio.purge(session, sink, encounter)
        if transcription.speaker_labels:
            transcription = replace(
                transcription,
                segments=apply_roles(transcription.segments, transcription.speaker_labels),
            )
        if not transcription.segments:
            # Le fournisseur n'est pas tombé, mais rien d'exploitable n'est revenu : la
            # trace doit le dire, sinon la panne se lira comme une réussite. Le volume
            # mesuré départage « micro muet » et « personne n'a parlé ».
            volume = niveau_audio
            if chunks and volume["crete"] < SEUIL_SILENCE:
                regle = "AUDIO_SILENT"
            elif chunks and est_une_note(volume):
                regle = "AUDIO_TEST_TONE"
            else:
                regle = "NO_TRANSCRIPT"
            registry.finish_run(
                session,
                stt_timer,
                status="failed",
                error_code=regle,
                model_version_id=stt_model.id,
                counters={"chunks": len(chunks), "segments": 0},
            )
            set_processing_errors(encounter, [{"rule": regle, "subject_id": str(encounter.id)}])
            transition(session, actor, encounter, "transcription_failed")
            logger.warning(
                "pipeline.transcription_failed", extra={"encounter_id": str(encounter.id)}
            )
            return encounter
        registry.finish_run(
            session,
            stt_timer,
            model_version_id=stt_model.id,
            counters={"chunks": len(chunks), "segments": len(transcription.segments)},
        )
        replace_segments(session, encounter.id, transcription.segments)
        session.commit()  # étape 1 visible : la transcription existe

    extractor = providers.clinical_extraction
    extraction_model = registry.model_version(
        session, "clinical_extraction", extractor.info.name, extractor.info.version
    )
    extraction_prompt = registry.prompt_version(
        session, "clinical_extraction", PROMPT_VERSION, SYSTEM_PROMPT
    )
    extraction_timer = registry.start_run("clinical_extraction", encounter.id)
    try:
        extraction = async_bridge.run(lambda: extractor.extract(transcription.segments, hints))
    except ExtractionUnavailable as error:
        registry.finish_run(
            session,
            extraction_timer,
            status="failed",
            error_code=error.code,
            model_version_id=extraction_model.id,
            prompt_version_id=extraction_prompt.id,
            counters={"segments": len(transcription.segments)},
        )
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
    registry.finish_run(
        session,
        extraction_timer,
        model_version_id=extraction_model.id,
        prompt_version_id=extraction_prompt.id,
        counters={"segments": len(transcription.segments), "facts": len(extraction.facts)},
    )
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
    session.commit()  # étape 2 visible : les faits cliniques sont enregistrés
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
    visit_kind: str = "consultation",
) -> Encounter:
    """Début de l'écoute. L'information du patient est une condition paramétrable (§65)."""
    if settings.patient_information_mode == "confirm" and not patient_informed:
        raise Conflict("PATIENT_INFORMATION_REQUIRED", str(encounter.id))
    transition(session, actor, encounter, "recording")
    audio.open_session(session, encounter)
    encounter.metadata_json = {**encounter.metadata_json, "visit_kind": visit_kind}
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


# --- Points marqués pendant l'écoute (spec §11) --------------------------------------
#
# Un point marqué dit « ce moment compte », pas ce qui s'y est dit. Il n'entre
# jamais dans l'objet clinique : il sert à retrouver l'endroit à la relecture.


def add_mark(
    session: Session, actor: Actor, encounter: Encounter, timestamp_ms: int
) -> EncounterMarkRow:
    if encounter.status not in {"recording", "paused"}:
        raise Conflict("INVALID_TRANSITION", str(encounter.id), [encounter.status, "recording"])
    existing = session.execute(
        select(EncounterMarkRow).where(
            EncounterMarkRow.encounter_id == encounter.id,
            EncounterMarkRow.timestamp_ms == timestamp_ms,
        )
    ).scalar_one_or_none()
    if existing is not None:  # geste répété au même instant : sans effet
        return existing
    mark = EncounterMarkRow(encounter_id=encounter.id, timestamp_ms=timestamp_ms)
    session.add(mark)
    session.flush()
    audit.record(session, actor, "encounter.mark_added", "encounter", encounter.id)
    return mark


def list_marks(session: Session, encounter: Encounter) -> list[EncounterMarkRow]:
    return list(
        session.execute(
            select(EncounterMarkRow)
            .where(EncounterMarkRow.encounter_id == encounter.id)
            .order_by(EncounterMarkRow.timestamp_ms)
        ).scalars()
    )


def validate_encounter(session: Session, actor: Actor, encounter: Encounter) -> Encounter:
    """La consultation est validée dès qu'un de ses documents l'est (décision du
    21/09/2026) : les documents sont indépendants, un plan encore en brouillon ne retient
    pas un compte rendu validé hors du dossier. Sans aucun document validé, refus."""
    if encounter.status in {"validated", "exported"}:
        return encounter
    active = [
        d for d in documents.list_documents(session, encounter.id) if d.status != "superseded"
    ]
    # Un document exporté (téléchargé, envoyé) l'a été après sa validation : il compte.
    if not any(d.status in {"validated", "exported"} for d in active):
        raise Conflict("DOCUMENTS_NOT_VALIDATED", str(encounter.id))
    transition(session, actor, encounter, "validated")
    return encounter
