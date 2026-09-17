"""Routes consultations, objet clinique, corrections et documents (spec §58)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from oris_api.api.dependencies import ActorDep, ProvidersDep, SessionDep, SettingsDep, SinkDep
from oris_api.api.presenters import document_out, encounter_out
from oris_api.api.schemas import (
    ClinicalObjectOut,
    CorrectionRequest,
    DocumentOut,
    DocumentValidate,
    EncounterCreate,
    EncounterFinish,
    EncounterOut,
    EncounterStart,
    LearningEventOut,
    ObjectVersionOut,
    TranscriptOut,
)
from oris_api.contracts.generated import ClinicalEncounterStatus
from oris_api.db.models import DocumentRow
from oris_api.services import clinical_store, corrections, documents, encounters, learning
from oris_api.services.errors import Conflict, NotFound

router = APIRouter(tags=["encounters"])


@router.get("/encounters", response_model=list[EncounterOut])
def list_encounters(
    session: SessionDep,
    actor: ActorDep,
    status: ClinicalEncounterStatus | None = None,
    patient_id: UUID | None = None,
) -> list[EncounterOut]:
    rows = encounters.list_encounters(session, actor, status, patient_id)
    return [encounter_out(session, row) for row in rows]


@router.post("/encounters", response_model=EncounterOut, status_code=status.HTTP_201_CREATED)
def create_encounter(body: EncounterCreate, session: SessionDep, actor: ActorDep) -> EncounterOut:
    encounter = encounters.create_encounter(session, actor, body.patient_id, body.synthetic_case_id)
    return encounter_out(session, encounter)


@router.get("/encounters/{encounter_id}", response_model=EncounterOut)
def get_encounter(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> EncounterOut:
    return encounter_out(session, encounters.get_encounter(session, actor, encounter_id))


def _transition(
    encounter_id: UUID, target: ClinicalEncounterStatus, session: SessionDep, actor: ActorDep
) -> EncounterOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    encounters.transition(session, actor, encounter, target)
    return encounter_out(session, encounter)


@router.post("/encounters/{encounter_id}/start", response_model=EncounterOut)
def start(
    encounter_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
    body: EncounterStart | None = None,
) -> EncounterOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    informed = body.patient_informed if body else False
    encounters.start(session, actor, encounter, settings, informed)
    return encounter_out(session, encounter)


@router.post("/encounters/{encounter_id}/pause", response_model=EncounterOut)
def pause(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> EncounterOut:
    return _transition(encounter_id, "paused", session, actor)


@router.post("/encounters/{encounter_id}/resume", response_model=EncounterOut)
def resume(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> EncounterOut:
    return _transition(encounter_id, "recording", session, actor)


@router.post("/encounters/{encounter_id}/finish", response_model=EncounterOut)
def finish(
    encounter_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
    sink: SinkDep,
    body: EncounterFinish | None = None,
) -> EncounterOut:
    """Fin de l'écoute puis traitement. 409 AUDIO_CHUNKS_MISSING s'il manque des segments."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    options = body or EncounterFinish()
    encounters.finish(
        session,
        actor,
        encounter,
        providers,
        sink,
        final_sequence=options.final_sequence,
        client_recorded_ms=options.client_recorded_ms,
        accept_gaps=options.accept_gaps,
    )
    return encounter_out(session, encounter)


@router.post("/encounters/{encounter_id}/process", response_model=EncounterOut)
def process(
    encounter_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
    sink: SinkDep,
) -> EncounterOut:
    """Relance du traitement après une erreur ; sans effet si déjà traité."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    encounters.process(session, actor, encounter, providers, sink)
    return encounter_out(session, encounter)


@router.post("/encounters/{encounter_id}/validate", response_model=EncounterOut)
def validate_encounter(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> EncounterOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    encounters.validate_encounter(session, actor, encounter)
    return encounter_out(session, encounter)


@router.get("/encounters/{encounter_id}/transcript", response_model=TranscriptOut)
def transcript(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> TranscriptOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return TranscriptOut(
        encounter_id=encounter.id, segments=clinical_store.load_segments(session, encounter.id)
    )


@router.get("/encounters/{encounter_id}/clinical-object", response_model=ClinicalObjectOut)
def clinical_object(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> ClinicalObjectOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return ClinicalObjectOut(
        clinical_object=clinical_store.load_current(session, encounter),
        versions=[
            ObjectVersionOut(
                version=v.version,
                change_kind=v.change_kind,
                created_at=v.created_at,
                created_by=v.created_by,
            )
            for v in clinical_store.list_versions(session, encounter.id)
        ],
    )


@router.patch("/encounters/{encounter_id}/clinical-object", response_model=EncounterOut)
def correct_clinical_object(
    encounter_id: UUID,
    body: CorrectionRequest,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> EncounterOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    corrections.apply_correction(
        session,
        actor,
        encounter,
        body.expected_object_version,
        body.operations,
        providers,
        regenerate=body.regenerate,
    )
    return encounter_out(session, encounter)


@router.get("/encounters/{encounter_id}/documents", response_model=list[DocumentOut])
def list_documents(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> list[DocumentOut]:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    result = []
    for document in documents.list_documents(session, encounter.id):
        version = documents.current_version(session, document)
        if version is not None:
            result.append(document_out(document, version, encounter.object_version))
    return result


@router.post("/encounters/{encounter_id}/documents/generate", response_model=list[DocumentOut])
def generate_documents(
    encounter_id: UUID, session: SessionDep, actor: ActorDep, providers: ProvidersDep
) -> list[DocumentOut]:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    if encounter.status not in {"review", "validated", "exported"}:
        raise Conflict("ENCOUNTER_NOT_PROCESSED", str(encounter.id))
    obj = clinical_store.load_current(session, encounter)
    documents.generate(session, encounter, obj, providers)
    if encounter.status != "review":
        encounters.transition(session, actor, encounter, "review")
    return list_documents(encounter_id, session, actor)


@router.post("/documents/{document_id}/validate", response_model=DocumentOut)
def validate_document(
    document_id: UUID, body: DocumentValidate, session: SessionDep, actor: ActorDep
) -> DocumentOut:
    document = documents.validate(session, actor, document_id, body.acknowledged_warning_codes)
    version = documents.current_version(session, document)
    encounter = encounters.get_encounter(session, actor, document.encounter_id)
    assert version is not None  # noqa: S101 - vérifié par la validation
    return document_out(document, version, encounter.object_version)


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, session: SessionDep, actor: ActorDep) -> DocumentOut:
    document = session.get(DocumentRow, document_id)
    if document is None:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    encounter = encounters.get_encounter(session, actor, document.encounter_id)
    version = documents.current_version(session, document)
    if version is None:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    return document_out(document, version, encounter.object_version)


@router.get("/encounters/{encounter_id}/learning-events", response_model=list[LearningEventOut])
def learning_events(
    encounter_id: UUID, session: SessionDep, actor: ActorDep
) -> list[LearningEventOut]:
    encounters.get_encounter(session, actor, encounter_id)
    return [
        LearningEventOut(
            learning_event_id=row.id,
            **{
                k: v
                for k, v in learning.to_contract(row).items()
                if k in LearningEventOut.model_fields and k != "learning_event_id"
            },
        )
        for row in learning.list_for_encounter(session, actor, encounter_id)
    ]
