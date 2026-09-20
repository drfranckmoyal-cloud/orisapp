"""Écran « Votre journée » : l'agenda du jour, lu chez Dental Lens.

La route ne fait que deux choses : demander la journée à Dental Lens, et dire pour
chaque rendez-vous si le patient a déjà un dossier dans Oris. Elle n'écrit rien —
créer le dossier passe par `POST /patients`, sur un geste du praticien.
"""

from __future__ import annotations

import unicodedata

from fastapi import APIRouter

from oris_api.api.dependencies import ActorDep, SessionDep, SettingsDep
from oris_api.api.schemas import JourneeOut, RendezVousOut
from oris_api.services import agenda, patients

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


@router.get("", response_model=JourneeOut)
def read_journee(
    session: SessionDep, actor: ActorDep, settings: SettingsDep, jour: str | None = None
) -> JourneeOut:
    journee = agenda.lire(settings, jour)
    connus = {_cle(p.first_name, p.last_name): p.id for p in patients.list_patients(session, actor)}
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
