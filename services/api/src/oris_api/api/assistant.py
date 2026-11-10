"""Le dialogue de correction et la relecture par Claude.

Deux temps, toujours : **comprendre** (rien ne change, Oris dit ce qu'il a compris), puis
**appliquer** (sur confirmation du praticien). Les faits passent par le chemin de
correction qui existe déjà ; la rédaction repasse par le rédacteur et tous ses garde-fous.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from oris_api.api.dependencies import ActorDep, ProvidersDep, SessionDep
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.db.models import DocumentRow, Encounter, Patient
from oris_api.domain.correction_intent import interpret
from oris_api.domain.corrections import CorrectionOperation
from oris_api.domain.preferences import Consigne, PreferencesPatch, ajouter_consigne
from oris_api.llm.assistant import PERMISES, AssistantIndisponible, Lecture
from oris_api.llm.redaction import REDIGES
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
from oris_api.services.errors import Conflict, NotFound, ServiceError, Unprocessable

router = APIRouter(tags=["assistant"])

Nature = Literal["dossier", "redaction", "civilite", "incompris"]
RELISIBLES = {"review", "validated", "exported"}


class ServiceIndisponible(ServiceError):
    """Le service d'IA ne répond pas : le code dit lequel de ses refus."""

    status_code = 503


class AssistantDemande(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demande: Annotated[str, Field(min_length=2, max_length=800)]


class AssistantLecture(BaseModel):
    """Ce qu'Oris a compris. Rien n'a changé."""

    nature: Nature
    resume: str
    consigne: str = ""
    civilite: str = ""
    operations: list[dict[str, Any]] = []
    question: str = ""
    #: « regles » : compris sans IA (dents, décisions) ; « claude » : compris par Claude.
    source: Literal["regles", "claude"]
    object_version: int


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
    lecture: Lecture, source: Literal["regles", "claude"], version: int
) -> AssistantLecture:
    return AssistantLecture(
        nature=lecture.nature,
        resume=lecture.resume,
        consigne=lecture.consigne,
        civilite=lecture.civilite,
        operations=[operation.model_dump(exclude_none=True) for operation in lecture.operations],
        question=lecture.question,
        source=source,
        object_version=version,
    )


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
    obj = clinical_store.load_current(session, encounter)
    regles = interpret(body.demande, obj)
    if regles.kind == "clinical":
        lecture = Lecture("dossier", regles.summary, operations=list(regles.operations))
        return _lecture_out(lecture, "regles", obj.object_version)

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
        return _lecture_out(lecture, "regles", obj.object_version)

    patient = session.get(Patient, encounter.patient_id)
    try:
        lecture = async_bridge.run(
            lambda: assistant.comprendre(body.demande, obj, patient.civility if patient else "")
        )
    except AssistantIndisponible as panne:
        raise ServiceIndisponible(panne.code, str(encounter.id)) from panne
    return _lecture_out(lecture, "claude", obj.object_version)


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
    """Applique ce que le praticien vient de confirmer."""
    encounter = encounters.get_encounter(session, actor, encounter_id)
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

    return AssistantResultat(
        applique=True, message=message, object_version=encounter.object_version
    )


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
    try:
        propositions = async_bridge.run(
            lambda: assistant.relire(document.document_type, rubriques, consignes)
        )
    except AssistantIndisponible as panne:
        raise ServiceIndisponible(panne.code, str(document_id)) from panne
    return RelectureOut(
        propositions=[
            PropositionOut(titre=p.titre, detail=p.detail, consigne=p.consigne)
            for p in propositions
        ]
    )


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
