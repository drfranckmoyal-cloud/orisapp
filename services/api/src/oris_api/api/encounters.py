"""Routes consultations, objet clinique, corrections et documents (spec §58)."""

from __future__ import annotations

import hashlib
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Header, Response, status
from sqlalchemy import func, select

from oris_api.api.dependencies import (
    ActorDep,
    LiveDep,
    MagasinDep,
    ProvidersDep,
    SessionDep,
    SettingsDep,
    SinkDep,
)
from oris_api.api.presenters import document_out, encounter_out
from oris_api.api.schemas import (
    ClinicalObjectOut,
    CorrectionRequest,
    DocumentOut,
    DocumentTextEdit,
    DocumentValidate,
    EncounterCreate,
    EncounterFinish,
    EncounterOut,
    EncounterStart,
    EtapeOut,
    LearningEventOut,
    LiveSegmentOut,
    LiveTranscriptOut,
    MarkCreate,
    MarkOut,
    ObjectVersionOut,
    PlanVueOut,
    ProgressOut,
    SpokenCorrectionOut,
    SpokenCorrectionRequest,
    TranscriptOut,
)
from oris_api.contracts.generated import ClinicalEncounterStatus
from oris_api.db.models import ClinicalFactRow, DocumentRow, TranscriptSegmentRow
from oris_api.domain.correction_intent import interpret
from oris_api.domain.types import AudioChunk
from oris_api.providers.base import TranscriptionUnavailable
from oris_api.services import (
    async_bridge,
    clinical_store,
    corrections,
    documents,
    encounters,
    learning,
    personalization,
)
from oris_api.services import audio as audio_service
from oris_api.services.documents import ExportFormat
from oris_api.services.errors import Conflict, NotFound, Unprocessable
from oris_api.services.live import FENETRE as LIVE_WINDOW

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
    encounter = encounters.create_encounter(
        session, actor, body.patient_id, body.synthetic_case_id, shadow=body.shadow
    )
    return encounter_out(session, encounter)


@router.get("/encounters/{encounter_id}", response_model=EncounterOut)
def get_encounter(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> EncounterOut:
    return encounter_out(session, encounters.get_encounter(session, actor, encounter_id))


@router.delete("/encounters/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_encounter(
    encounter_id: UUID, session: SessionDep, actor: ActorDep, sink: SinkDep
) -> None:
    """Supprimer une consultation. 409 ENCOUNTER_IN_PROGRESS pendant l'écoute ou le traitement."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    encounters.delete_encounter(session, actor, encounter, sink)


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
    providers: ProvidersDep,
    live: LiveDep,
    body: EncounterStart | None = None,
) -> EncounterOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    informed = body.patient_informed if body else False
    kind = body.visit_kind if body else "consultation"
    encounters.start(session, actor, encounter, settings, informed, kind)
    # L'écoute en direct est un confort : si elle ne s'ouvre pas, la consultation part
    # quand même. Rien de ce qu'elle produit n'entre dans le dossier (§14.1).
    if providers.live_speech_to_text is not None:
        live.open(
            encounter.id,
            providers.live_speech_to_text,
            "fr-FR",
            personalization.hints_for(session, encounter.practitioner_id),
        )
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
    live: LiveDep,
    body: EncounterFinish | None = None,
) -> EncounterOut:
    """Fin de l'écoute puis traitement. 409 AUDIO_CHUNKS_MISSING s'il manque des segments."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    # Le direct s'arrête ici. La transcription du dossier est refaite sur l'audio
    # complet, jamais reprise du direct (§14.1).
    live.close(encounter.id)
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


@router.get("/encounters/{encounter_id}/live", response_model=LiveTranscriptOut)
def read_live_transcript(
    encounter_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
    live: LiveDep,
) -> LiveTranscriptOut:
    """Ce qu'Oris entend, à l'instant (§11, §14.1).

    Vue provisoire : elle sert à voir que le micro capte et que les mots tombent juste.
    Elle n'est jamais la source du compte rendu.
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    if providers.live_speech_to_text is None:
        return LiveTranscriptOut(state="disabled", segments=[], total=0, reconnections=0)
    session_live = live.snapshot(encounter.id)
    if session_live is None:
        return LiveTranscriptOut(state="idle", segments=[], total=0, reconnections=0)
    recents = session_live.segments[-LIVE_WINDOW:]
    return LiveTranscriptOut(
        state=session_live.state,
        error_code=session_live.error_code,
        segments=[
            LiveSegmentOut(
                segment_id=segment.segment_id,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                speaker_role=segment.speaker_role,
                text=segment.text,
                is_final=segment.is_final,
            )
            for segment in recents
        ],
        total=len(session_live.segments),
        reconnections=session_live.reconnections,
    )


@router.get("/encounters/{encounter_id}/progress", response_model=ProgressOut)
def read_progress(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> ProgressOut:
    """Où en est le traitement, d'après la base — jamais une progression inventée (S06)."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    segments = session.scalar(
        select(func.count())
        .select_from(TranscriptSegmentRow)
        .where(TranscriptSegmentRow.encounter_id == encounter.id)
    )
    facts = session.scalar(
        select(func.count())
        .select_from(ClinicalFactRow)
        .where(ClinicalFactRow.encounter_id == encounter.id)
    )
    produced = [
        document
        for document in documents.list_documents(session, encounter.id)
        if document.status != "superseded"
    ]
    return ProgressOut(
        status=encounter.status,
        transcript_segments=segments or 0,
        facts=facts or 0,
        documents=len(produced),
        termine=encounter.status not in {"finalizing", "processing"},
    )


@router.post(
    "/encounters/{encounter_id}/marks",
    response_model=MarkOut,
    status_code=status.HTTP_201_CREATED,
)
def add_mark(encounter_id: UUID, body: MarkCreate, session: SessionDep, actor: ActorDep) -> MarkOut:
    """Marquer un moment de l'écoute. Ne touche jamais au dossier clinique (§11)."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    mark = encounters.add_mark(session, actor, encounter, body.timestamp_ms)
    session.commit()
    return MarkOut(timestamp_ms=mark.timestamp_ms, created_at=mark.created_at)


@router.get("/encounters/{encounter_id}/marks", response_model=list[MarkOut])
def list_marks(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> list[MarkOut]:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return [
        MarkOut(timestamp_ms=mark.timestamp_ms, created_at=mark.created_at)
        for mark in encounters.list_marks(session, encounter)
    ]


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


@router.post("/encounters/{encounter_id}/corrections/text", response_model=SpokenCorrectionOut)
def correct_from_speech(
    encounter_id: UUID,
    body: SpokenCorrectionRequest,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> SpokenCorrectionOut:
    """Correction dictée ou écrite : aperçu du patch, puis application sur confirmation.

    Rien n'est deviné : une commande ambiguë revient au praticien avec la raison.
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    obj = clinical_store.load_current(session, encounter)
    reading = interpret(body.command, obj)
    applied = False

    if body.apply and reading.kind == "clinical":
        if body.expected_object_version is None:
            raise Conflict("OBJECT_VERSION_REQUIRED", str(encounter.id))
        corrections.apply_correction(
            session,
            actor,
            encounter,
            body.expected_object_version,
            reading.operations,
            providers,
        )
        applied = True
    elif body.apply and reading.kind == "editorial":
        # §46 B : une préférence de rédaction ne touche pas au dossier clinique ;
        # elle est retenue pour l'apprentissage, et rien d'autre.
        learning.emit(
            session,
            actor,
            encounter.id,
            obj.object_version,
            "style_preference_detected",
            None,
            {"preference": reading.preference},
        )
        applied = True

    return SpokenCorrectionOut(
        kind=reading.kind,
        summary=reading.summary,
        impact=reading.impact,
        reason=reading.reason,
        candidates=reading.candidates,
        operations=[operation.model_dump() for operation in reading.operations],
        applied=applied,
        object_version=encounter.object_version,
    )


@router.post("/encounters/{encounter_id}/corrections/voice", response_model=SpokenCorrectionOut)
def correct_from_voice(
    encounter_id: UUID,
    payload: Annotated[bytes, Body(media_type=audio_service.AUDIO_FORMAT)],
    content_type: Annotated[str, Header()],
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
    apply: bool = False,
    expected_object_version: int | None = None,
) -> SpokenCorrectionOut:
    """Correction dictée au micro : transcrite, interprétée, jamais conservée.

    L'audio d'une correction ne traverse pas le stockage : il est transcrit dans la
    requête, puis oublié (D010).
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    if content_type.replace(" ", "").lower() != audio_service.AUDIO_FORMAT:
        raise Unprocessable("UNSUPPORTED_AUDIO_FORMAT", str(encounter.id))
    if not payload or len(payload) % 2:
        raise Unprocessable("INVALID_CHUNK", str(encounter.id))

    chunk = AudioChunk(
        session_id=str(encounter.id),
        sequence=0,
        timestamp_ms=0,
        checksum=hashlib.sha256(payload).hexdigest(),
        payload=payload,
    )
    try:
        transcription = async_bridge.run(
            lambda: providers.speech_to_text.transcribe([chunk], encounters.LOCALE, [])
        )
    except TranscriptionUnavailable as error:
        raise Conflict("STT_UNAVAILABLE", str(encounter.id), [error.code]) from error

    command = " ".join(segment.text for segment in transcription.segments).strip()
    return correct_from_speech(
        encounter_id,
        SpokenCorrectionRequest(
            command=command or " ",
            apply=apply,
            expected_object_version=expected_object_version,
        ),
        session,
        actor,
        providers,
    )


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


@router.post(
    "/encounters/{encounter_id}/documents/operative-note", response_model=list[DocumentOut]
)
def generate_operative_note(
    encounter_id: UUID, session: SessionDep, actor: ActorDep, providers: ProvidersDep
) -> list[DocumentOut]:
    """Compte rendu de soins, à la demande du praticien (§81) : jamais d'office."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    if encounter.status not in {"review", "validated", "exported"}:
        raise Conflict("ENCOUNTER_NOT_PROCESSED", str(encounter.id))
    obj = clinical_store.load_current(session, encounter)
    if not documents.operative_note_available(obj):
        raise Conflict("NO_PROCEDURE_TO_DOCUMENT", str(encounter.id))
    # Seulement ce document : les autres, peut-être déjà validés, ne bougent pas, et la
    # consultation garde son statut (les documents sont indépendants).
    documents.generate(
        session, encounter, obj, providers, include=["operative_note"], seulement=True
    )
    return list_documents(encounter_id, session, actor)


@router.post(
    "/encounters/{encounter_id}/documents/referral-letter", response_model=list[DocumentOut]
)
def generate_referral_letter(
    encounter_id: UUID, session: SessionDep, actor: ActorDep, providers: ProvidersDep
) -> list[DocumentOut]:
    """Courrier d'adressage, à la demande : bâti sur les faits, jamais d'office."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    if encounter.status not in {"review", "validated", "exported"}:
        raise Conflict("ENCOUNTER_NOT_PROCESSED", str(encounter.id))
    obj = clinical_store.load_current(session, encounter)
    if not obj.facts:
        raise Conflict("NOTHING_TO_REFER", str(encounter.id))
    # Seulement ce document : les autres, peut-être déjà validés, ne bougent pas, et la
    # consultation garde son statut (les documents sont indépendants).
    documents.generate(
        session, encounter, obj, providers, include=["referral_letter"], seulement=True
    )
    return list_documents(encounter_id, session, actor)


@router.get("/encounters/{encounter_id}/plan-vue", response_model=PlanVueOut)
def plan_view(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> PlanVueOut:
    """Le plan de traitement mis en forme pour le schéma et la chronologie."""
    from oris_api.documents.plan import plan_vue

    encounter = encounters.get_encounter(session, actor, encounter_id)
    vue = plan_vue(
        clinical_store.load_current(session, encounter),
        documents.titres_du_plan(session, encounter.id),
    )

    def sortie(etape: Any) -> EtapeOut:
        return EtapeOut(
            titre=etape.titre,
            rang=etape.rang,
            dents=list(etape.dents),
            details=list(etape.details),
            statut=etape.statut,
            delai=etape.delai,
            couleur=etape.couleur,
            fact_ids=list(etape.fact_ids),
        )

    return PlanVueOut(
        numerote=vue.numerote,
        etapes=[sortie(e) for e in vue.etapes],
        ecartes=[sortie(e) for e in vue.ecartes],
        dents_absentes=list(vue.dents_absentes),
    )


@router.post("/documents/{document_id}/text", response_model=DocumentOut)
def edit_document_text(
    document_id: UUID, body: DocumentTextEdit, session: SessionDep, actor: ActorDep
) -> DocumentOut:
    """Le praticien réécrit le texte. Le dossier clinique, lui, ne bouge pas (§48)."""
    document = documents.edit_text(session, actor, document_id, body.content)
    version = documents.current_version(session, document)
    encounter = encounters.get_encounter(session, actor, document.encounter_id)
    if version is None:
        raise Conflict("DOCUMENT_EMPTY", str(document_id))
    return document_out(document, version, encounter.object_version)


@router.post("/documents/{document_id}/validate", response_model=DocumentOut)
def validate_document(
    document_id: UUID, body: DocumentValidate, session: SessionDep, actor: ActorDep
) -> DocumentOut:
    document = documents.validate(session, actor, document_id, body.acknowledged_warning_codes)
    version = documents.current_version(session, document)
    encounter = encounters.get_encounter(session, actor, document.encounter_id)
    # Un document validé suffit à valider la consultation : les documents sont
    # indépendants, les autres se valident quand le praticien le décide.
    if encounter.status == "review":
        encounters.validate_encounter(session, actor, encounter)
    assert version is not None  # noqa: S101 - vérifié par la validation
    return document_out(document, version, encounter.object_version)


@router.get(
    "/documents/{document_id}/export",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "text/plain": {}}}},
)
def export_document(
    document_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    magasin: MagasinDep,
    format: ExportFormat = "pdf",
) -> Response:
    """Sortie d'un document : PDF à imprimer, ou texte à coller dans le logiciel métier."""
    exported = documents.export_document(session, actor, document_id, format, magasin)
    return Response(
        content=exported.payload,
        media_type=exported.media_type,
        headers={"content-disposition": f'attachment; filename="{exported.filename}"'},
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, session: SessionDep, actor: ActorDep) -> None:
    """Retirer un courrier d'adressage ou un compte rendu opératoire demandé par erreur.
    Tout document se supprime ; le dossier clinique, lui, reste."""
    documents.supprimer(session, actor, document_id)


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
