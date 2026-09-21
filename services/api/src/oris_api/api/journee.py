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
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy.orm import Session

from oris_api.api.dependencies import ActorDep, SessionDep, SettingsDep
from oris_api.api.schemas import DepotOut, JourneeDepot, JourneeOut, JourOut, RendezVousOut
from oris_api.services import agenda, patients
from oris_api.services.errors import Forbidden, Unprocessable
from oris_api.services.identity import Actor

router = APIRouter(prefix="/journee", tags=["journee"])

#: Le dépôt n'est ouvert qu'à cette machine. L'extension tourne sur le Mac du praticien,
#: dans sa session Chrome ; rien d'autre n'a de raison de déposer un agenda.
LOCALES = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"})


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
    client = request.client.host if request.client else ""
    if client not in LOCALES:
        raise Forbidden("DEPOT_NON_LOCAL")

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
