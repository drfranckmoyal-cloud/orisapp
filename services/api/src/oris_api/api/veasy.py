"""Veasy : déposer un document dans le dossier du patient (Franck, 25/11/2026).

Deux côtés, comme pour SmileCloud :
- le praticien demande le dépôt d'un document **validé** (fenêtre d'envoi) ;
- l'extension Chrome, dans la session Veasy du praticien, lit les demandes, retire le
  PDF, le dépose, et dit ce qu'il en est. Contrat : `docs/DEPOT_VEASY.md`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Request, Response
from pydantic import BaseModel, Field

from oris_api.api.dependencies import (
    ActorDep,
    MagasinDep,
    SessionDep,
    SettingsDep,
    extension_autorisee,
)
from oris_api.api.smilecloud import DEPOSABLE, TITRES_DOCUMENT
from oris_api.config import Settings
from oris_api.db.models import Patient
from oris_api.services import audit, documents, encounters, patients, veasy
from oris_api.services.errors import NotFound, Unprocessable
from oris_api.services.identity import Actor

router = APIRouter(tags=["veasy"])


# --- Côté extension -------------------------------------------------------------------


class PatientVeasyOut(BaseModel):
    """De quoi retrouver le dossier dans Veasy, et rien de plus."""

    prenom: str
    nom: str
    #: AAAA-MM-JJ, ou vide si la fiche Oris ne la porte pas.
    date_naissance: str
    #: Le numéro Veasy déjà appris par un dépôt précédent, sinon vide.
    veasy_id: str


class DemandeVeasyOut(BaseModel):
    id: str
    document_id: str
    nom_fichier: str
    patient: PatientVeasyOut
    demande_le: str
    essais: int = 0


class DepotVeasyFaitIn(BaseModel):
    id: str = Field(max_length=64)
    #: Vide quand c'est fait ; sinon ce qui a empêché le dépôt, dit au praticien.
    raison: str = Field(default="", max_length=300)
    #: Rien n'est parti et ça vaut la peine de recommencer : la demande reste ouverte.
    reessayer: bool = False
    #: Le numéro du patient dans Veasy, quand le dossier a été trouvé.
    veasy_patient_id: str = Field(default="", max_length=32)


@router.get("/veasy/demandes", response_model=list[DemandeVeasyOut])
def demandes(
    request: Request, settings: SettingsDep, authorization: str | None = Header(default=None)
) -> list[DemandeVeasyOut]:
    extension_autorisee(request, settings, authorization)
    return [DemandeVeasyOut(**d) for d in veasy.en_attente(settings)]


@router.get("/veasy/depot/{demande_id}")
def retirer_le_document(
    demande_id: str,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    magasin: MagasinDep,
    authorization: str | None = Header(default=None),
) -> Response:
    """Le PDF à déposer, fabriqué à la demande, remis, et oublié."""
    extension_autorisee(request, settings, authorization)
    d = veasy.demande(settings, demande_id)
    if d is None:
        raise NotFound("DEMANDE_INCONNUE", demande_id)
    acteur = Actor(UUID(d["organisation_id"]), UUID(d["praticien_id"]))
    sortie = documents.export_document(session, acteur, UUID(d["document_id"]), "pdf", magasin)
    return Response(
        content=sortie.payload,
        media_type=sortie.media_type,
        headers={"content-disposition": f'attachment; filename="{sortie.filename}"'},
    )


@router.post("/veasy/depose")
def noter_depot(
    body: DepotVeasyFaitIn,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    """L'extension a déposé le document — ou dit pourquoi non.

    Un dépôt réussi apprend à Oris le numéro Veasy du patient, s'il ne le savait pas :
    jamais par-dessus un numéro déjà retenu.
    """
    extension_autorisee(request, settings, authorization)
    d = veasy.noter(
        settings,
        body.id,
        raison=body.raison,
        reessayer=body.reessayer,
        veasy_patient_id=body.veasy_patient_id,
    )
    if d is None:
        raise NotFound("DEMANDE_INCONNUE", body.id)
    if not body.raison and body.veasy_patient_id and d.get("patient_id"):
        patient = session.get(Patient, UUID(d["patient_id"]))
        if patient is not None and not patient.veasy_id:
            patient.veasy_id = body.veasy_patient_id
            audit.record(
                session,
                None,
                "patient.updated",
                "patient",
                patient.id,
                organization_id=patient.organization_id,
                fields=["veasy_id"],
            )
    return {"note": True}


# --- Côté praticien -------------------------------------------------------------------


class DepotVeasyOut(BaseModel):
    """Où en est le dépôt d'un document dans Veasy."""

    #: « absent » (jamais demandé), « en_attente », « depose », « impossible ».
    etat: str
    demande_le: str | None = None
    depose_le: str | None = None
    raison: str = ""


def _etat(settings: Settings, document_id: UUID) -> DepotVeasyOut:
    dernier = veasy.dernier_depot(settings, document_id)
    if dernier is None:
        return DepotVeasyOut(etat="absent")
    if not dernier.get("termine"):
        return DepotVeasyOut(
            etat="en_attente", demande_le=dernier["demande_le"], raison=dernier.get("raison", "")
        )
    raison = dernier.get("raison", "")
    return DepotVeasyOut(
        etat="impossible" if raison else "depose",
        demande_le=dernier["demande_le"],
        depose_le=dernier.get("depose_le"),
        raison=raison,
    )


@router.get("/documents/{document_id}/veasy", response_model=DepotVeasyOut)
def etat_depot(
    document_id: UUID, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> DepotVeasyOut:
    documents.get_document(session, actor, document_id)
    return _etat(settings, document_id)


@router.post("/documents/{document_id}/veasy", response_model=DepotVeasyOut)
def deposer_dans_veasy(
    document_id: UUID, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> DepotVeasyOut:
    """Ranger ce document dans le dossier Veasy du patient.

    Seul un document validé part : ce qui entre dans le dossier médical y reste.
    """
    document = documents.get_document(session, actor, document_id)
    encounter = encounters.get_encounter(session, actor, document.encounter_id)
    patient = patients.get_patient(session, actor, encounter.patient_id)
    # Comme pour SmileCloud : le dossier se vérifie avant le premier dépôt (Franck,
    # 25/11/2026). Un compte rendu dans le mauvais dossier est la faute à ne jamais faire.
    if not patient.veasy_id:
        raise Unprocessable("VEASY_NON_RELIE")
    if documents.current_version(session, document) is None:
        raise Unprocessable("DOCUMENT_EMPTY")
    if document.status not in DEPOSABLE:
        raise Unprocessable("DOCUMENT_NOT_VALIDATED")
    veasy.demander_depot(
        settings,
        document_id=document_id,
        nom_fichier=f"Oris - {TITRES_DOCUMENT.get(document.document_type, 'document')}.pdf",
        patient={
            "prenom": patient.first_name,
            "nom": patient.last_name,
            "date_naissance": patient.birth_date.isoformat() if patient.birth_date else "",
            "veasy_id": patient.veasy_id or "",
        },
        patient_id=patient.id,
        organisation_id=actor.organization_id,
        praticien_id=actor.user_id,
    )
    return _etat(settings, document_id)


# --- Relier le patient à son dossier Veasy -------------------------------------------


class DossierVeasyIn(BaseModel):
    veasy_id: str = Field(max_length=32)
    nom: str = Field(max_length=200)
    date_naissance: str = Field(default="", max_length=10)


class DossiersVeasyIn(BaseModel):
    dossiers: list[DossierVeasyIn] = Field(max_length=50_000)


@router.post("/veasy/dossiers")
def deposer_dossiers(
    body: DossiersVeasyIn,
    request: Request,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, int]:
    """La liste des dossiers Veasy, relevée par l'extension."""
    extension_autorisee(request, settings, authorization)
    return {"dossiers": veasy.deposer_dossiers(settings, [d.model_dump() for d in body.dossiers])}


class CandidatVeasyOut(BaseModel):
    veasy_id: str
    nom: str
    date_naissance: str
    pour_cent: int


class VeasyPatientOut(BaseModel):
    veasy_id: str | None
    #: Le nom du dossier relié, tel que Veasy l'écrit (si la liste le connaît).
    nom: str | None
    #: « relie », « trouve », « a_confirmer », « ambigu », « absent », « sans_liste ».
    etat: str
    candidats: list[CandidatVeasyOut]


class LienVeasyIn(BaseModel):
    #: Le numéro du dossier Veasy, ou `null` pour délier.
    veasy_id: str | None = Field(default=None, max_length=32)


def _vue(settings: Settings, patient: Patient) -> VeasyPatientOut:
    if patient.veasy_id:
        connu = veasy.dossier(settings, patient.veasy_id)
        return VeasyPatientOut(
            veasy_id=patient.veasy_id,
            nom=connu["nom"] if connu else None,
            etat="relie",
            candidats=[],
        )
    if not veasy.dossiers(settings):
        return VeasyPatientOut(veasy_id=None, nom=None, etat="sans_liste", candidats=[])
    proposition = veasy.proposer(settings, f"{patient.first_name} {patient.last_name}")
    candidats = []
    for c in proposition.candidats:
        d = veasy.dossier(settings, c.cle) or {}
        candidats.append(
            CandidatVeasyOut(
                veasy_id=c.cle,
                nom=c.nom,
                date_naissance=d.get("date_naissance", ""),
                pour_cent=c.pour_cent,
            )
        )
    return VeasyPatientOut(veasy_id=None, nom=None, etat=proposition.etat, candidats=candidats)


@router.get("/patients/{patient_id}/veasy", response_model=VeasyPatientOut)
def lire_lien(
    patient_id: UUID, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> VeasyPatientOut:
    return _vue(settings, patients.get_patient(session, actor, patient_id))


@router.put("/patients/{patient_id}/veasy", response_model=VeasyPatientOut)
def relier(
    patient_id: UUID,
    body: LienVeasyIn,
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
) -> VeasyPatientOut:
    """Le praticien confirme le dossier Veasy de ce patient — ou le délie.

    Un numéro saisi à la main est accepté (il se lit dans Veasy) : la liste des dossiers
    n'est pas indispensable pour relier un patient qu'on connaît."""
    patient = patients.get_patient(session, actor, patient_id)
    numero = (body.veasy_id or "").strip()
    if numero and not numero.isdigit():
        raise Unprocessable("VEASY_NUMERO_INVALIDE")
    patient.veasy_id = numero or None
    audit.record(session, actor, "patient.updated", "patient", patient.id, fields=["veasy_id"])
    session.flush()
    return _vue(settings, patient)
