"""SmileCloud : routes de l'extension (ce Mac seulement) et du dossier patient.

Contrat avec l'extension Chrome : `docs/PIECES_JOINTES_SMILECLOUD.md`, § « Contrat ».
"""

from __future__ import annotations

import hmac
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Header, Request
from pydantic import BaseModel, Field

from oris_api.api.dependencies import (
    ActorDep,
    MagasinDep,
    SessionDep,
    SettingsDep,
    depuis_cette_machine,
)
from oris_api.config import Settings
from oris_api.services import attachments, patients, smilecloud
from oris_api.services.errors import Forbidden, NotFound, Unprocessable
from oris_api.services.identity import Actor

router = APIRouter(tags=["smilecloud"])


def _extension(request: Request, settings: Settings, authorization: str | None) -> None:
    """L'extension tourne sur ce Mac ; le secret partagé de la journée, s'il est posé,
    vaut aussi ici."""
    if not depuis_cette_machine(request):
        raise Forbidden("DEPOT_NON_LOCAL")
    attendu = settings.journee_depot_token
    if attendu is not None:
        entete = authorization or ""
        presente = entete[7:].strip() if entete.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(presente, attendu.get_secret_value()):
            raise Forbidden("DEPOT_JETON_INVALIDE")


# --- Côté extension -------------------------------------------------------------------


class DossierIn(BaseModel):
    nom: str = Field(max_length=200)
    case_id: str = Field(max_length=64)


class DossiersIn(BaseModel):
    dossiers: list[DossierIn] = Field(max_length=20_000)


class FichierGalerieIn(BaseModel):
    res_id: str = Field(max_length=64)
    nom: str = Field(default="", max_length=200)
    nature: str = Field(default="autre", max_length=20)


class GalerieIn(BaseModel):
    id: str = Field(default="", max_length=80)
    nom: str = Field(default="", max_length=200)
    date: str = Field(default="", max_length=40)
    fichiers: list[FichierGalerieIn] = Field(default_factory=list, max_length=2_000)


class GaleriesIn(BaseModel):
    case_id: str = Field(max_length=64)
    galeries: list[GalerieIn] = Field(max_length=500)


class DemandeExtensionOut(BaseModel):
    id: str
    type: Literal["galeries", "fichiers"]
    case_id: str
    demande_le: str
    fichiers: list[str] | None = None


class EcartIn(BaseModel):
    demande: str
    res_id: str
    raison: str = Field(max_length=80)


@router.post("/smilecloud/dossiers")
def deposer_dossiers(
    body: DossiersIn,
    request: Request,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, int]:
    """La liste des dossiers SmileCloud, relevée par l'extension."""
    _extension(request, settings, authorization)
    try:
        return {
            "dossiers": smilecloud.deposer_dossiers(
                settings, [d.model_dump() for d in body.dossiers]
            )
        }
    except smilecloud.SmileCloudInvalide as erreur:
        raise Unprocessable("SMILECLOUD_INVALIDE", details=[str(erreur)]) from erreur


@router.get("/smilecloud/demandes", response_model=list[DemandeExtensionOut])
def demandes(
    request: Request, settings: SettingsDep, authorization: str | None = Header(default=None)
) -> list[DemandeExtensionOut]:
    """Ce qu'Oris attend de l'extension : lire des galeries, rapatrier des fichiers."""
    _extension(request, settings, authorization)
    return [DemandeExtensionOut(**d) for d in smilecloud.demandes_en_attente(settings)]


@router.post("/smilecloud/galeries")
def deposer_galeries(
    body: GaleriesIn,
    request: Request,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, int]:
    _extension(request, settings, authorization)
    try:
        n = smilecloud.deposer_galeries(
            settings, body.case_id, [g.model_dump() for g in body.galeries]
        )
    except smilecloud.SmileCloudInvalide as erreur:
        raise Unprocessable("SMILECLOUD_INVALIDE", details=[str(erreur)]) from erreur
    return {"galeries": n}


@router.post("/smilecloud/fichier")
def recevoir_fichier(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    magasin: MagasinDep,
    contenu: Annotated[bytes, Body(media_type="application/octet-stream")],
    x_demande: Annotated[str, Header(max_length=64)],
    x_res_id: Annotated[str, Header(max_length=64)],
    x_nom: Annotated[str, Header(max_length=200)],
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Un original lu dans SmileCloud, rangé dans le dossier du patient. Refus dits."""
    _extension(request, settings, authorization)
    d = smilecloud.demande(settings, x_demande)
    if d is None or d["type"] != "fichiers":
        raise NotFound("DEMANDE_INCONNUE", x_demande)
    acteur = Actor(UUID(d["organisation_id"]), UUID(d["praticien_id"]))
    patient = patients.get_patient(session, acteur, UUID(d["patient_id"]))
    galerie = next((f["galerie"] for f in d["fichiers"] if f["res_id"] == x_res_id), "")
    try:
        piece = attachments.add_attachment(
            session, acteur, magasin, patient, x_nom, contenu, label=f"SmileCloud · {galerie}"[:200]
        )
    except Unprocessable as refus:
        # Le refus se dit dans le compte rendu de la récupération, jamais en silence.
        suivi = smilecloud.noter_ecarte(settings, x_demande, x_res_id, refus.code)
        return {"recu": False, "raison": refus.code, "termine": suivi["termine"]}
    session.commit()
    suivi = smilecloud.noter_recu(settings, x_demande, x_res_id)
    return {"recu": True, "piece": str(piece.id), "termine": suivi["termine"]}


@router.post("/smilecloud/ecarte")
def ecarter(
    body: EcartIn,
    request: Request,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    """L'extension n'a pas pu lire ce fichier (ou l'a reconnu comme vidéo, CBCT…)."""
    _extension(request, settings, authorization)
    try:
        suivi = smilecloud.noter_ecarte(settings, body.demande, body.res_id, body.raison)
    except smilecloud.SmileCloudInvalide as erreur:
        raise NotFound("DEMANDE_INCONNUE", body.demande) from erreur
    return {"termine": bool(suivi["termine"])}


# --- Côté dossier patient -------------------------------------------------------------


class CandidatOut(BaseModel):
    case_id: str
    nom: str
    pour_cent: int


class FichierOut(BaseModel):
    res_id: str
    nom: str
    nature: str
    rapatriable: bool


class GalerieOut(BaseModel):
    id: str
    nom: str
    date: str
    fichiers: list[FichierOut]


class RecuperationOut(BaseModel):
    demande: str
    total: int
    recus: int
    ecartes: list[dict[str, str]]
    termine: bool
    demande_le: str


class SmileCloudPatientOut(BaseModel):
    #: Le dossier SmileCloud relié à ce patient, s'il l'est.
    case_id: str | None
    nom: str | None
    #: Sinon : « trouve », « a_confirmer », « ambigu », « absent », ou « sans_liste »
    #: quand l'extension n'a encore livré aucune liste de dossiers.
    etat: str
    candidats: list[CandidatOut]
    galeries: list[GalerieOut] | None
    galeries_lues_le: str | None
    lecture_en_cours: bool
    recuperation: RecuperationOut | None


class LienIn(BaseModel):
    case_id: str | None = Field(default=None, max_length=64)


class RecupererIn(BaseModel):
    fichiers: list[str] = Field(min_length=1, max_length=500)


def _vue(settings: Settings, patient: Any) -> SmileCloudPatientOut:
    case_id = patient.smilecloud_case_id
    tous = smilecloud.dossiers(settings)
    candidats: list[CandidatOut]
    if case_id:
        etat, candidats = "relie", []
    elif not tous:
        etat, candidats = "sans_liste", []
    else:
        proposition = smilecloud.proposer(settings, f"{patient.first_name} {patient.last_name}")
        etat = proposition.etat
        candidats = [
            CandidatOut(case_id=c.cle, nom=c.nom, pour_cent=c.pour_cent)
            for c in proposition.candidats
        ]
    lues = smilecloud.lire_galeries(settings, case_id) if case_id else None
    recup = smilecloud.derniere_recuperation(settings, patient.id)
    return SmileCloudPatientOut(
        case_id=case_id,
        nom=smilecloud.nom_du_dossier(settings, case_id) if case_id else None,
        etat=etat,
        candidats=candidats,
        galeries=[
            GalerieOut(
                id=g["id"],
                nom=g["nom"],
                date=g["date"],
                fichiers=[
                    FichierOut(
                        res_id=f["res_id"],
                        nom=f["nom"],
                        nature=f["nature"],
                        rapatriable=f["nature"] not in smilecloud.NATURES_EXCLUES,
                    )
                    for f in g["fichiers"]
                ],
            )
            for g in lues["galeries"]
        ]
        if lues
        else None,
        galeries_lues_le=lues["lu_le"] if lues else None,
        lecture_en_cours=bool(case_id) and smilecloud.galeries_en_attente(settings, case_id),
        recuperation=RecuperationOut(
            demande=recup["id"],
            total=len(recup["fichiers"]) + len(recup["ecartes"]) - _hors_demande(recup),
            recus=len(recup["recus"]),
            ecartes=recup["ecartes"],
            termine=bool(recup["termine"]),
            demande_le=recup["demande_le"],
        )
        if recup
        else None,
    )


def _hors_demande(recup: dict[str, Any]) -> int:
    demandes = {f["res_id"] for f in recup["fichiers"]}
    return sum(1 for e in recup["ecartes"] if e["res_id"] in demandes)


@router.get("/patients/{patient_id}/smilecloud", response_model=SmileCloudPatientOut)
def etat_patient(
    patient_id: UUID, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> SmileCloudPatientOut:
    return _vue(settings, patients.get_patient(session, actor, patient_id))


@router.put("/patients/{patient_id}/smilecloud", response_model=SmileCloudPatientOut)
def relier(
    patient_id: UUID, body: LienIn, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> SmileCloudPatientOut:
    """Relier (ou délier) le patient à son dossier SmileCloud. Un geste du praticien."""
    patient = patients.get_patient(session, actor, patient_id)
    if body.case_id is not None and not smilecloud.MOTIF_CASE_ID.match(body.case_id):
        raise Unprocessable("SMILECLOUD_INVALIDE")
    patients.update_patient(session, actor, patient_id, {"smilecloud_case_id": body.case_id})
    session.commit()
    return _vue(settings, patient)


@router.post("/patients/{patient_id}/smilecloud/galeries", response_model=SmileCloudPatientOut)
def lire_galeries(
    patient_id: UUID, session: SessionDep, actor: ActorDep, settings: SettingsDep
) -> SmileCloudPatientOut:
    """Demander à l'extension de relire les galeries du dossier relié."""
    patient = patients.get_patient(session, actor, patient_id)
    if not patient.smilecloud_case_id:
        raise Unprocessable("SMILECLOUD_NON_RELIE")
    smilecloud.demander_galeries(settings, patient.smilecloud_case_id)
    return _vue(settings, patient)


@router.post("/patients/{patient_id}/smilecloud/recuperer", response_model=SmileCloudPatientOut)
def recuperer(
    patient_id: UUID,
    body: RecupererIn,
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
) -> SmileCloudPatientOut:
    """Rapatrier les fichiers cochés. Vidéos et CBCT sont écartés d'office, et le disent."""
    patient = patients.get_patient(session, actor, patient_id)
    if not patient.smilecloud_case_id:
        raise Unprocessable("SMILECLOUD_NON_RELIE")
    smilecloud.demander_fichiers(
        settings,
        patient.smilecloud_case_id,
        patient.id,
        actor.organization_id,
        actor.user_id,
        body.fichiers,
    )
    return _vue(settings, patient)
