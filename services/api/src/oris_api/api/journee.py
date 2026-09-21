"""Écran « Votre journée » : l'agenda du jour, lu chez Dental Lens.

Deux lectures seulement : la journée choisie, et l'aperçu de la semaine qui tient dans
la colonne de gauche. Ni l'une ni l'autre n'écrit : créer un dossier passe par
`POST /patients`, sur un geste du praticien.
"""

from __future__ import annotations

import unicodedata
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.orm import Session

from oris_api.api.dependencies import ActorDep, SessionDep, SettingsDep
from oris_api.api.schemas import JourneeOut, JourOut, RendezVousOut
from oris_api.services import agenda, patients
from oris_api.services.identity import Actor

router = APIRouter(prefix="/journee", tags=["journee"])


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
        source=journee.source,
        disponible=journee.disponible,
        lu_le=journee.lu_le,
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
