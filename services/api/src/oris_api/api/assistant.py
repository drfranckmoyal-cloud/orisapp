"""Le dialogue de correction et la relecture par Claude.

Deux temps, toujours : **comprendre** (rien ne change, Oris dit ce qu'il a compris), puis
**appliquer** (sur confirmation du praticien). Les faits passent par le chemin de
correction qui existe déjà ; la rédaction repasse par le rédacteur et tous ses garde-fous.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Body, Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.api.dependencies import ActorDep, ProvidersDep, SessionDep
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.db.models import DemandeCorrectionRow, DocumentRow, Encounter, Patient
from oris_api.domain.correction_intent import interpret
from oris_api.domain.corrections import CorrectionOperation
from oris_api.domain.preferences import Consigne, PreferencesPatch, ajouter_consigne
from oris_api.domain.types import AudioChunk
from oris_api.llm.assistant import PERMISES, AssistantIndisponible, Lecture
from oris_api.llm.redaction import REDIGES
from oris_api.providers.base import TranscriptionUnavailable
from oris_api.providers.factory import ProviderSet
from oris_api.services import (
    async_bridge,
    audit,
    clinical_store,
    corrections,
    documents,
    encounters,
    learning,
    personalization,
)
from oris_api.services import audio as audio_service
from oris_api.services.errors import Conflict, NotFound, ServiceError, Unprocessable
from oris_api.services.identity import Actor

router = APIRouter(tags=["assistant"])

Nature = Literal["dossier", "redaction", "civilite", "incompris"]
RELISIBLES = {"review", "validated", "exported"}


class ServiceIndisponible(ServiceError):
    """Le service d'IA ne répond pas : le code dit lequel de ses refus."""

    status_code = 503


class AssistantDemande(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demande: Annotated[str, Field(min_length=2, max_length=800)]
    #: Le document qu'on regardait : il s'affiche avec la demande dans l'historique.
    document_id: UUID | None = None


class AssistantLecture(BaseModel):
    """Ce qu'Oris a compris. Rien n'a changé."""

    nature: Nature
    #: La demande telle qu'elle a été lue — ou entendue, quand elle est dictée.
    demande: str = ""
    resume: str
    consigne: str = ""
    civilite: str = ""
    operations: list[dict[str, Any]] = []
    question: str = ""
    #: « regles » : compris sans IA (dents, décisions) ; « claude » : compris par Claude.
    source: Literal["regles", "claude"]
    object_version: int
    #: La demande telle qu'elle est gardée dans l'historique de la consultation.
    demande_id: UUID | None = None


class AssistantApplication(BaseModel):
    """Ce que le praticien confirme."""

    model_config = ConfigDict(extra="forbid")
    nature: Literal["dossier", "redaction", "civilite"]
    operations: list[CorrectionOperation] = []
    expected_object_version: Annotated[int, Field(ge=1)] | None = None
    consignes: Annotated[list[Consigne], Field(max_length=5)] = []
    #: Retenir les consignes pour tous les documents suivants, pas seulement celui-ci.
    retenir: bool = False
    civilite: Literal["monsieur", "madame"] | None = None
    #: Le document à réécrire ; absent, tous les documents rédigés de la consultation.
    document_id: UUID | None = None
    #: La demande de l'historique que cette application conclut.
    demande_id: UUID | None = None


class AssistantResultat(BaseModel):
    applique: bool
    message: str
    object_version: int


class PropositionOut(BaseModel):
    titre: str
    detail: str
    consigne: str


class RelectureOut(BaseModel):
    propositions: list[PropositionOut]
    demande_id: UUID | None = None


EtatDemande = Literal[
    "lecture", "proposee", "relecture", "application", "traitee", "annulee", "incomprise", "echec"
]


class DemandeOut(BaseModel):
    """Une demande de l'historique, et ce qu'elle est devenue."""

    id: UUID
    document_id: UUID | None
    texte: str
    etat: EtatDemande
    lecture: AssistantLecture | None = None
    propositions: list[PropositionOut] = []
    #: Le message final : ce qui a été fait, ou pourquoi rien ne l'a été.
    message: str = ""
    #: Le code d'erreur, quand la demande n'a pas abouti : chaque appareil le traduit.
    code: str = ""
    created_at: datetime
    #: Depuis quand elle est dans son état (la barre de progression part de là).
    depuis: datetime


def _noter(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    texte: str,
    etat: str,
    reponse: dict[str, Any],
    document_id: UUID | None,
) -> DemandeCorrectionRow:
    """Garde la demande dans l'historique de la consultation."""
    demande = DemandeCorrectionRow(
        encounter_id=encounter.id,
        document_id=document_id,
        user_id=actor.user_id,
        texte=texte[:800],
        etat=etat,
        reponse=reponse,
    )
    session.add(demande)
    session.flush()
    return demande


def _demande(session: Session, encounter: Encounter, demande_id: UUID) -> DemandeCorrectionRow:
    demande = session.get(DemandeCorrectionRow, demande_id)
    if demande is None or demande.encounter_id != encounter.id:
        raise NotFound("DEMANDE_NOT_FOUND", str(demande_id))
    return demande


def _poser(demande: DemandeCorrectionRow, etat: str, **reponse: Any) -> None:
    demande.etat = etat
    # Un nouveau dictionnaire : SQLAlchemy ne voit pas une clé changée en place.
    demande.reponse = {**demande.reponse, **reponse}
    demande.updated_at = datetime.now(UTC)


class ConsignesOut(BaseModel):
    #: Dites pour cette consultation seulement.
    consultation: list[str]
    #: Retenues pour tous les documents du praticien.
    praticien: list[str]


class ConsignesConsultation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consultation: Annotated[list[Consigne], Field(max_length=20)]


def _fictive(encounter: Encounter) -> bool:
    return isinstance(encounter.metadata_json.get("synthetic_case_id"), str)


def _lecture_out(
    lecture: Lecture, source: Literal["regles", "claude"], version: int, demande: str = ""
) -> AssistantLecture:
    return AssistantLecture(
        nature=lecture.nature,
        demande=demande,
        resume=lecture.resume,
        consigne=lecture.consigne,
        civilite=lecture.civilite,
        operations=[operation.model_dump(exclude_none=True) for operation in lecture.operations],
        question=lecture.question,
        source=source,
        object_version=version,
    )


def _comprendre(
    session: Session, encounter: Encounter, demande: str, providers: ProviderSet
) -> AssistantLecture:
    obj = clinical_store.load_current(session, encounter)
    regles = interpret(demande, obj)
    if regles.kind == "clinical":
        lecture = Lecture("dossier", regles.summary, operations=list(regles.operations))
        return _lecture_out(lecture, "regles", obj.object_version, demande)

    assistant = None if _fictive(encounter) else providers.assistant
    if assistant is None:
        if regles.kind == "editorial":
            lecture = Lecture(
                "redaction",
                f"Consigne de rédaction : {regles.preference}.",
                consigne=regles.preference,
            )
        else:
            raison = regles.reason or "Je n'ai pas compris ce qu'il faut changer."
            lecture = Lecture("incompris", raison, question=raison)
        return _lecture_out(lecture, "regles", obj.object_version, demande)

    patient = session.get(Patient, encounter.patient_id)
    try:
        lecture = async_bridge.run(
            lambda: assistant.comprendre(demande, obj, patient.civility if patient else "")
        )
    except AssistantIndisponible as panne:
        raise ServiceIndisponible(panne.code, str(encounter.id)) from panne
    return _lecture_out(lecture, "claude", obj.object_version, demande)


@router.post("/encounters/{encounter_id}/assistant", response_model=AssistantLecture)
def comprendre(
    encounter_id: UUID,
    body: AssistantDemande,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> AssistantLecture:
    """Dit ce que la demande change — le dossier, la rédaction, la civilité — sans rien changer.

    Les tournures connues (« remplace 26 par 27 ») sont comprises sans IA : c'est
    immédiat, et cela marche même quand le service d'IA ne répond pas. Le reste va à
    Claude, sauf pour une consultation fictive, dont rien ne sort d'Oris.
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return _comprendre_et_noter(
        session, actor, encounter, body.demande.strip(), providers, body.document_id
    )


def _comprendre_et_noter(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    texte: str,
    providers: ProviderSet,
    document_id: UUID | None,
) -> AssistantLecture:
    """Comprend la demande et la garde dans l'historique — panne comprise."""
    try:
        lecture = _comprendre(session, encounter, texte, providers)
    except ServiceIndisponible as panne:
        _noter(session, actor, encounter, texte, "echec", {"code": panne.code}, document_id)
        # La demande ratée reste dans l'historique : on l'enregistre avant de répondre.
        session.commit()
        raise
    etat = "incomprise" if lecture.nature == "incompris" else "proposee"
    demande = _noter(
        session,
        actor,
        encounter,
        texte,
        etat,
        {"lecture": lecture.model_dump(mode="json")},
        document_id,
    )
    return lecture.model_copy(update={"demande_id": demande.id})


@router.post("/encounters/{encounter_id}/assistant/voix", response_model=AssistantLecture)
def comprendre_a_la_voix(
    encounter_id: UUID,
    payload: Annotated[bytes, Body(media_type=audio_service.AUDIO_FORMAT)],
    content_type: Annotated[str, Header()],
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> AssistantLecture:
    """La même demande, dictée : transcrite dans la requête, jamais conservée (D010)."""
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
    demande = " ".join(segment.text for segment in transcription.segments).strip()
    if len(demande) < 2:
        raison = "Je n'ai rien entendu. Redites votre demande, ou écrivez-la."
        obj = clinical_store.load_current(session, encounter)
        return _lecture_out(
            Lecture("incompris", raison, question=raison), "regles", obj.object_version
        )
    return _comprendre_et_noter(session, actor, encounter, demande, providers, None)


def _a_reecrire(
    session: Session, encounter: Encounter, document_id: UUID | None
) -> list[DocumentDocumentType]:
    """Les documents que la demande réécrit : celui qu'on regarde, ou tous les rédigés."""
    if document_id is not None:
        document = session.get(DocumentRow, document_id)
        if document is None or document.encounter_id != encounter.id:
            raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
        return [cast(DocumentDocumentType, document.document_type)]
    return [
        cast(DocumentDocumentType, document.document_type)
        for document in documents.list_documents(session, encounter.id)
        if document.document_type in REDIGES
    ]


def _reecrire(
    session: Session,
    encounter: Encounter,
    providers: ProviderSet,
    document_id: UUID | None,
) -> int:
    types = _a_reecrire(session, encounter, document_id)
    if not types:
        return 0
    obj = clinical_store.load_current(session, encounter)
    documents.generate(session, encounter, obj, providers, include=types, seulement=True)
    return len(types)


@router.post("/encounters/{encounter_id}/assistant/appliquer", response_model=AssistantResultat)
def appliquer(
    encounter_id: UUID,
    body: AssistantApplication,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> AssistantResultat:
    """Applique ce que le praticien vient de confirmer.

    La demande de l'historique passe « en cours » et c'est enregistré tout de suite : un
    autre appareil, ou l'app rouverte, voit qu'Oris travaille. Elle finit « traitée », ou
    « non aboutie » avec la raison.
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    demande = _demande(session, encounter, body.demande_id) if body.demande_id else None
    if demande is not None:
        _poser(demande, "application")
        session.commit()
    try:
        message = _appliquer(session, actor, encounter, body, providers)
    except ServiceError as refus:
        session.rollback()
        if demande is not None:
            demande = _demande(session, encounter, demande.id)
            _poser(demande, "echec", code=refus.code)
            session.commit()
        raise
    if demande is not None:
        _poser(demande, "traitee", message=message)
    return AssistantResultat(
        applique=True, message=message, object_version=encounter.object_version
    )


def _appliquer(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    body: AssistantApplication,
    providers: ProviderSet,
) -> str:
    if encounter.status not in RELISIBLES:
        raise Conflict("ENCOUNTER_NOT_PROCESSED", str(encounter.id))

    if body.nature == "dossier":
        if not body.operations or not all(isinstance(o, PERMISES) for o in body.operations):
            raise Unprocessable("CORRECTION_REJECTED", str(encounter.id))
        if body.expected_object_version is None:
            raise Conflict("OBJECT_VERSION_REQUIRED", str(encounter.id))
        corrections.apply_correction(
            session, actor, encounter, body.expected_object_version, body.operations, providers
        )
        message = "Dossier corrigé ; les documents sont mis à jour."

    elif body.nature == "redaction":
        if not body.consignes:
            raise Unprocessable("CONSIGNE_REQUIRED", str(encounter.id))
        courantes = documents.consignes_de(encounter)
        for consigne in body.consignes:
            courantes = ajouter_consigne(courantes, consigne)
        documents.poser_consignes(encounter, courantes)
        if body.retenir:
            retenues = personalization.preferences_of(session, actor).consignes
            for consigne in body.consignes:
                retenues = ajouter_consigne(retenues, consigne)
            personalization.update_preferences(session, actor, PreferencesPatch(consignes=retenues))
        obj = clinical_store.load_current(session, encounter)
        for consigne in body.consignes:
            # §46 B : une préférence de rédaction ne touche pas au dossier clinique ;
            # elle est retenue pour l'apprentissage.
            learning.emit(
                session,
                actor,
                encounter.id,
                obj.object_version,
                "style_preference_detected",
                None,
                {"preference": consigne, "retenue": body.retenir},
            )
        session.flush()
        nombre = _reecrire(session, encounter, providers, body.document_id)
        message = (
            "Document rédigé à nouveau avec votre consigne."
            if nombre
            else "Consigne notée ; aucun document à réécrire."
        )
        if body.retenir:
            message += " Elle vaudra aussi pour les suivants."

    else:
        if body.civilite is None:
            raise Unprocessable("CIVILITE_REQUIRED", str(encounter.id))
        patient = session.get(Patient, encounter.patient_id)
        if patient is None:
            raise NotFound("PATIENT_NOT_FOUND", str(encounter.patient_id))
        patient.civility = body.civilite
        audit.record(session, actor, "patient.updated", "patient", patient.id, fields=["civility"])
        session.flush()
        _reecrire(session, encounter, providers, body.document_id)
        message = "Civilité enregistrée dans la fiche ; le document est accordé."

    return message


@router.post("/documents/{document_id}/relecture", response_model=RelectureOut)
def relire(
    document_id: UUID, session: SessionDep, actor: ActorDep, providers: ProvidersDep
) -> RelectureOut:
    """Claude relit le document et propose des améliorations de forme. Rien n'est changé."""
    document, encounter = documents.document_et_consultation(session, actor, document_id)
    version = documents.current_version(session, document)
    if version is None:
        raise Conflict("DOCUMENT_EMPTY", str(document_id))
    if document.document_type not in REDIGES:
        raise Conflict("RELECTURE_NON_PROPOSEE", str(document_id))
    assistant = None if _fictive(encounter) else providers.assistant
    if assistant is None:
        raise ServiceIndisponible("ASSISTANT_UNAVAILABLE", str(document_id))

    # Rubrique par rubrique quand le document vient du rédacteur ; le texte entier quand
    # le praticien l'a réécrit à la main.
    rubriques: list[dict[str, str]] = []
    for claim in version.claims or []:
        titre = str(claim.get("section", ""))
        if rubriques and rubriques[-1]["titre"] == titre:
            rubriques[-1]["texte"] += " " + str(claim.get("text", ""))
        else:
            rubriques.append({"titre": titre, "texte": str(claim.get("text", ""))})
    if not rubriques:
        rubriques = [{"titre": "", "texte": version.content}]

    consignes = [
        *personalization.preferences_of(session, actor).consignes,
        *documents.consignes_de(encounter),
    ]
    texte = "Relis ce document et propose des améliorations."
    try:
        propositions = async_bridge.run(
            lambda: assistant.relire(document.document_type, rubriques, consignes)
        )
    except AssistantIndisponible as panne:
        _noter(session, actor, encounter, texte, "echec", {"code": panne.code}, document.id)
        session.commit()
        raise ServiceIndisponible(panne.code, str(document_id)) from panne
    sorties = [
        PropositionOut(titre=p.titre, detail=p.detail, consigne=p.consigne) for p in propositions
    ]
    if sorties:
        demande = _noter(
            session,
            actor,
            encounter,
            texte,
            "relecture",
            {"propositions": [s.model_dump() for s in sorties]},
            document.id,
        )
    else:
        demande = _noter(
            session,
            actor,
            encounter,
            texte,
            "traitee",
            {"message": "Rien à proposer : le document se lit bien tel qu'il est."},
            document.id,
        )
    return RelectureOut(propositions=sorties, demande_id=demande.id)


@router.get("/encounters/{encounter_id}/assistant", response_model=list[DemandeOut])
def historique(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> list[DemandeOut]:
    """La conversation de la consultation, de la première demande à la dernière.

    Elle est la même sur l'iPhone et sur le site, et survit à l'app fermée.
    """
    encounter = encounters.get_encounter(session, actor, encounter_id)
    demandes = session.scalars(
        select(DemandeCorrectionRow)
        .where(DemandeCorrectionRow.encounter_id == encounter.id)
        .order_by(DemandeCorrectionRow.created_at)
    )
    sorties: list[DemandeOut] = []
    for d in demandes:
        reponse = d.reponse or {}
        lecture = reponse.get("lecture")
        sorties.append(
            DemandeOut(
                id=d.id,
                document_id=d.document_id,
                texte=d.texte,
                etat=cast(EtatDemande, d.etat),
                lecture=AssistantLecture.model_validate(lecture) if lecture else None,
                propositions=[
                    PropositionOut.model_validate(p) for p in reponse.get("propositions", [])
                ],
                message=str(reponse.get("message", "")),
                code=str(reponse.get("code", "")),
                created_at=d.created_at,
                depuis=d.updated_at,
            )
        )
    return sorties


@router.post("/encounters/{encounter_id}/assistant/{demande_id}/annuler", response_model=DemandeOut)
def annuler(
    encounter_id: UUID, demande_id: UUID, session: SessionDep, actor: ActorDep
) -> DemandeOut:
    """Le praticien écarte une proposition : rien n'a changé, et c'est noté."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    demande = _demande(session, encounter, demande_id)
    if demande.etat in {"proposee", "relecture", "incomprise"}:
        _poser(demande, "annulee")
        session.flush()
    return next(d for d in historique(encounter_id, session, actor) if d.id == demande.id)


@router.get("/encounters/{encounter_id}/consignes", response_model=ConsignesOut)
def lire_consignes(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> ConsignesOut:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return ConsignesOut(
        consultation=documents.consignes_de(encounter),
        praticien=personalization.preferences_of(session, actor).consignes,
    )


@router.put("/encounters/{encounter_id}/consignes", response_model=ConsignesOut)
def remplacer_consignes(
    encounter_id: UUID, body: ConsignesConsultation, session: SessionDep, actor: ActorDep
) -> ConsignesOut:
    """Retirer une consigne dite pour cette consultation (celles du praticien se gèrent
    dans ses préférences). Le document n'est pas réécrit : il le sera à la prochaine demande."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
    documents.poser_consignes(encounter, list(body.consultation))
    session.flush()
    return ConsignesOut(
        consultation=documents.consignes_de(encounter),
        praticien=personalization.preferences_of(session, actor).consignes,
    )
