"""Écran « Votre journée » : l'agenda du jour, déposé par l'extension Chrome.

Trois routes. Deux lectures pour l'écran — la journée choisie, et l'aperçu de la semaine
qui tient dans la colonne de gauche. Et un dépôt, par lequel l'extension livre la journée
qu'elle vient de relever dans Doctolib.

Le dépôt **n'écrit aucun patient en base**. Il range la journée, rien de plus : faire
entrer un patient dans Oris reste un geste du praticien (spec §58).
"""

from __future__ import annotations

import hmac
import unicodedata
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy.orm import Session

from oris_api.api.dependencies import ActorDep, SessionDep, SettingsDep
from oris_api.api.schemas import (
    DemandeIn,
    DemandeOut,
    DepotOut,
    JourneeDepot,
    JourneeOut,
    JourOut,
    RendezVousOut,
)
from oris_api.services import agenda, patients
from oris_api.services.errors import Forbidden, Unprocessable
from oris_api.services.identity import Actor

router = APIRouter(prefix="/journee", tags=["journee"])

#: Le dépôt n'est ouvert qu'à cette machine. L'extension tourne sur le Mac du praticien,
#: dans sa session Chrome ; rien d'autre n'a de raison de déposer un agenda.
LOCALES = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"})


def _seulement_ici(request: Request) -> None:
    """Ce que l'extension appelle n'est ouvert qu'à cette machine.

    L'extension tourne sur le Mac du praticien, dans sa session Chrome ; rien d'autre
    n'a de raison de déposer un agenda ni de savoir ce qu'Oris attend.
    """
    if (request.client.host if request.client else "") not in LOCALES:
        raise Forbidden("DEPOT_NON_LOCAL")


def _cle(prenom: str, nom: str) -> tuple[str, str]:
    """Clé de rapprochement insensible à la casse et aux accents.

    Doctolib écrit « MOREAU Chloé », Oris « Moreau Chloe » : sans cette mise à plat,
    le même patient apparaîtrait deux fois et on lui créerait un second dossier.
    """

    def plat(mot: str) -> str:
        sans = unicodedata.normalize("NFKD", mot.strip().casefold())
        return "".join(c for c in sans if not unicodedata.combining(c))

    return plat(prenom), plat(nom)


def _dossiers_connus(session: Session, actor: Actor) -> dict[tuple[str, str], UUID]:
    return {_cle(p.first_name, p.last_name): p.id for p in patients.list_patients(session, actor)}


@router.get("", response_model=JourneeOut)
def read_journee(
    session: SessionDep, actor: ActorDep, settings: SettingsDep, jour: str | None = None
) -> JourneeOut:
    journee = agenda.lire(settings, jour)
    connus = _dossiers_connus(session, actor)
    return JourneeOut(
        jour=journee.jour,
        agenda=journee.agenda,
        disponible=journee.disponible,
        recu_le=journee.recu_le,
        demande_le=agenda.demande_pour(settings, journee.jour),
        rendezvous=[
            RendezVousOut(
                heure=rdv.heure,
                prenom=rdv.prenom,
                nom=rdv.nom,
                motif=rdv.motif,
                statut=rdv.statut,
                smilecloud=rdv.smilecloud,
                patient_id=connus.get(_cle(rdv.prenom, rdv.nom)),
            )
            for rdv in journee.rendezvous
        ],
    )


@router.get("/semaine", response_model=list[JourOut])
def read_semaine(
    session: SessionDep, actor: ActorDep, settings: SettingsDep, depuis: str, jours: int = 7
) -> list[JourOut]:
    """L'état de chaque jour de la semaine : combien de patients, combien de dossiers
    manquants. De quoi passer d'un jour à l'autre sans les ouvrir un par un."""
    connus = _dossiers_connus(session, actor)
    return [
        JourOut(
            jour=journee.jour,
            lu=journee.disponible,
            patients=len(journee.rendezvous),
            a_creer=sum(1 for rdv in journee.rendezvous if _cle(rdv.prenom, rdv.nom) not in connus),
        )
        for journee in agenda.lire_semaine(settings, depuis, jours)
    ]


@router.post("/demande", response_model=DemandeOut)
def demander_journee(body: DemandeIn, actor: ActorDep, settings: SettingsDep) -> DemandeOut:
    """Demander à l'extension de (re)lire cet agenda.

    Oris ne va rien chercher : il pose une demande, que l'extension vient lire à son
    prochain passage et sert en déposant la journée. Rien n'est écrit d'autre que la
    demande elle-même.
    """
    try:
        quand = agenda.demander(settings, body.jour)
    except agenda.JourneeInvalide as erreur:
        raise Unprocessable("JOURNEE_INVALIDE", details=[str(erreur)]) from erreur
    return DemandeOut(jour=body.jour or date.today().isoformat(), demande_le=quand)


@router.get("/demandes", response_model=list[DemandeOut])
def read_demandes(request: Request, settings: SettingsDep) -> list[DemandeOut]:
    """Les journées qu'Oris attend. Lu par l'extension, sur cette machine seulement."""
    _seulement_ici(request)
    return [
        DemandeOut(jour=jour, demande_le=quand) for jour, quand in agenda.demandes(settings).items()
    ]


@router.post("/depot", response_model=DepotOut)
def deposer_journee(
    request: Request,
    body: JourneeDepot,
    settings: SettingsDep,
    authorization: str | None = Header(default=None),
) -> DepotOut:
    """Recevoir une journée relevée dans Doctolib par l'extension Chrome.

    Pas de praticien connecté ici : c'est une livraison de machine à machine, sur cette
    machine seulement. Et surtout, **aucun patient n'est créé** — la journée est rangée,
    le praticien décide ensuite, ligne par ligne, laquelle mérite un dossier.
    """
    _seulement_ici(request)

    attendu = settings.journee_depot_token
    if attendu is not None:
        entete = authorization or ""
        presente = entete[7:].strip() if entete.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(presente, attendu.get_secret_value()):
            raise Forbidden("DEPOT_JETON_INVALIDE")

    try:
        depot = agenda.deposer(settings, body.model_dump())
    except agenda.JourneeInvalide as erreur:
        raise Unprocessable("JOURNEE_INVALIDE", details=[str(erreur)]) from erreur
    return DepotOut(
        jour=depot.jour, rendezvous=depot.rendezvous, remplace=depot.remplace, raison=depot.raison
    )
