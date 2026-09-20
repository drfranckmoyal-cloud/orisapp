"""Agenda du jour, lu depuis Dental Lens (écran « Votre journée »).

Oris ne parle pas à Doctolib et n'a pas à le faire. C'est **Dental Lens**, l'autre
outil du cabinet, qui lit l'agenda dans le navigateur et dépose la journée sur le
poste : un fichier par jour dans son registre, et un petit serveur local qui, en
prime, rapproche chaque patient de son dossier SmileCloud.

Oris vient se servir, et rien d'autre. Deux chemins, dans cet ordre :

1. le **serveur** Dental Lens s'il répond — on récupère alors l'état SmileCloud de
   chaque rendez-vous ;
2. sinon le **fichier** du jour, qui reste lisible même serveur éteint.

Cette lecture n'écrit rien. Faire entrer un patient de l'agenda dans Oris reste un
geste explicite du praticien (§58) : tant qu'il ne clique pas, aucun nom venu de
Doctolib n'atteint la base.

Invariant de journalisation (CLAUDE.md) : aucun nom de patient, aucun motif de
rendez-vous ne sort d'ici dans un log. On ne compte que des lignes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import httpx

from oris_api.config import Settings

log = logging.getLogger(__name__)

Source = Literal["serveur", "fichier", "absent"]
EtatSmileCloud = Literal["trouve", "absent", "a_verifier", "ambigu", "demande", "inconnu"]

#: États que Dental Lens sait produire. Tout autre mot devient « inconnu » plutôt
#: que d'être affiché tel quel : un écran ne montre pas un mot qu'il ne comprend pas.
ETATS: frozenset[str] = frozenset({"trouve", "absent", "a_verifier", "ambigu", "demande"})

#: Court exprès. Si Dental Lens ne tourne pas, on ne fait pas attendre l'écran :
#: on bascule sur le fichier du jour.
DELAI_SERVEUR = 1.5


@dataclass(frozen=True, slots=True)
class RendezVous:
    heure: str
    prenom: str
    nom: str
    motif: str
    statut: str
    smilecloud: EtatSmileCloud


@dataclass(frozen=True, slots=True)
class Journee:
    jour: str
    agenda: str
    source: Source
    lu_le: str | None
    rendezvous: tuple[RendezVous, ...]

    @property
    def disponible(self) -> bool:
        return self.source != "absent"


def _texte(valeur: object) -> str:
    return valeur.strip() if isinstance(valeur, str) else ""


def _etat(valeur: object) -> EtatSmileCloud:
    mot = _texte(valeur)
    return mot if mot in ETATS else "inconnu"  # type: ignore[return-value]


def _rendez_vous(brut: object) -> RendezVous | None:
    """Une ligne d'agenda, ou rien si elle n'a même pas de nom.

    Dental Lens sépare déjà « M. URBAN Eric » en prénom/nom ; on ne refait pas ce
    travail ici. Mais un agenda peut contenir des lignes qui ne sont pas des
    patients (pause, blocage) : sans nom exploitable, la ligne est écartée.
    """
    if not isinstance(brut, dict):
        return None
    prenom, nom = _texte(brut.get("prenom")), _texte(brut.get("nom"))
    if not nom and not prenom:
        return None
    return RendezVous(
        heure=_texte(brut.get("heure")),
        prenom=prenom,
        nom=nom.upper(),
        motif=_texte(brut.get("motif")),
        statut=_texte(brut.get("statut")),
        smilecloud=_etat(brut.get("recherche")),
    )


def _journee(brut: object, jour: str, source: Source) -> Journee | None:
    if not isinstance(brut, dict):
        return None
    lignes = brut.get("rendezvous")
    if not isinstance(lignes, list):
        return None
    rdv = tuple(filter(None, (_rendez_vous(ligne) for ligne in lignes)))
    return Journee(
        jour=_texte(brut.get("jour")) or jour,
        agenda=_texte(brut.get("agenda")),
        source=source,
        lu_le=_texte(brut.get("lu_le")) or None,
        rendezvous=rdv,
    )


def _par_le_serveur(base_url: str, jour: str) -> Journee | None:
    """La journée telle que Dental Lens la voit, rapprochement SmileCloud compris."""
    try:
        reponse = httpx.get(
            f"{base_url.rstrip('/')}/api/journee", params={"jour": jour}, timeout=DELAI_SERVEUR
        )
        reponse.raise_for_status()
        return _journee(reponse.json(), jour, "serveur")
    except (httpx.HTTPError, json.JSONDecodeError):
        # Serveur éteint : ce n'est pas une panne, c'est le cas courant. On se rabat.
        log.info("Dental Lens ne répond pas ; lecture du fichier du jour")
        return None


def _par_le_fichier(registre: Path, jour: str) -> Journee | None:
    fichier = registre / "journees" / f"{jour}.json"
    try:
        return _journee(json.loads(fichier.read_text(encoding="utf-8")), jour, "fichier")
    except (OSError, json.JSONDecodeError):
        return None


def lire(settings: Settings, jour: str | None = None) -> Journee:
    """La journée demandée, ou une journée vide si personne ne l'a déposée.

    Une journée absente n'est pas une erreur : elle veut dire « Dental Lens n'a pas
    encore lu cet agenda ». L'écran le dit, il n'invente pas de rendez-vous.
    """
    jour = jour or date.today().isoformat()
    vide = Journee(jour=jour, agenda="", source="absent", lu_le=None, rendezvous=())
    if settings.agenda_provider != "dental_lens":
        return vide
    lue = _par_le_serveur(settings.dental_lens_url, jour) or _par_le_fichier(
        settings.dental_lens_registre, jour
    )
    if lue is None:
        return vide
    log.info("Journée %s lue via %s : %d rendez-vous", jour, lue.source, len(lue.rendezvous))
    return lue
