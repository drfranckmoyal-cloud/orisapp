"""Routes de l'envoi des documents par courriel."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from oris_api.api.dependencies import ActorDep, MagasinDep, SessionDep, SettingsDep
from oris_api.api.schemas import (
    BoiteEnvoiOut,
    CandidatOut,
    EnvoiIn,
    EnvoiPrepareOut,
    ResultatEnvoiOut,
)
from oris_api.db.models import DocumentRow, Encounter, Patient, User
from oris_api.services import documents, envoi
from oris_api.services.courriel import Messagerie

router = APIRouter(tags=["envoi"])


def messagerie(request: Request) -> Messagerie | None:
    boite: Messagerie | None = request.app.state.messagerie
    return boite


MessagerieDep = Annotated[Messagerie | None, Depends(messagerie)]


@router.get("/me/boite-envoi", response_model=BoiteEnvoiOut)
def boite_envoi(
    session: SessionDep, actor: ActorDep, settings: SettingsDep, boite: MessagerieDep
) -> BoiteEnvoiOut:
    adresse, raison = envoi.etat_boite(
        session.get(User, actor.user_id), settings, boite is not None
    )
    return BoiteEnvoiOut(
        adresse=adresse,
        configure=raison is None,
        raison=raison,
        serveur=f"{settings.smtp_host}:{settings.smtp_port}",
    )


@router.get("/documents/{document_id}/envoi", response_model=EnvoiPrepareOut)
def preparer_envoi(
    document_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
    boite: MessagerieDep,
) -> EnvoiPrepareOut:
    prepare = envoi.preparer(session, actor, document_id, settings, boite is not None)
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    patient = session.get(Patient, encounter.patient_id) if encounter else None
    moment = (encounter.started_at or encounter.created_at) if encounter else None
    nom = (
        documents.nom_de_fichier(document.document_type, patient, moment)
        if document and moment
        else "document.pdf"
    )
    return EnvoiPrepareOut(
        expediteur=prepare.expediteur,
        configure=prepare.configure,
        raison=prepare.raison,
        candidats=[CandidatOut(**c.__dict__) for c in prepare.candidats],
        objet=prepare.objet,
        message=prepare.message,
        brouillon=prepare.brouillon,
        nom_fichier=nom,
    )


@router.post("/documents/{document_id}/envoi", response_model=list[ResultatEnvoiOut])
def envoyer(
    document_id: UUID,
    body: EnvoiIn,
    session: SessionDep,
    actor: ActorDep,
    settings: SettingsDep,
    boite: MessagerieDep,
    magasin: MagasinDep,
) -> list[ResultatEnvoiOut]:
    """Un courriel par destinataire, le document en PDF joint ; chaque envoi est noté."""
    resultats = envoi.envoyer(
        session,
        actor,
        document_id,
        body.destinataires,
        body.adresses,
        body.objet,
        body.message,
        settings,
        boite,
        magasin,
    )
    return [ResultatEnvoiOut(**r.__dict__) for r in resultats]
