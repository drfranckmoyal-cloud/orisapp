"""Agenda du jour, **déposé** par l'extension Chrome (écran « Votre journée »).

Oris ne lit pas Doctolib et ne va rien chercher chez personne. L'extension de Dental
Lens lit l'agenda dans la session ouverte du praticien, puis livre la journée à chaque
destinataire qu'elle connaît ; Oris en est un. Il reçoit, il range, il affiche.

Conséquence voulue : Oris n'a besoin de rien d'autre que lui-même pour montrer la
journée. Dental Lens peut être éteint, désinstallé, remplacé.

Une journée déposée est rangée **hors de la base clinique**, dans un fichier par date.
Ce sont de vrais noms de patients, et ils n'ont rien à faire dans le dossier clinique
tant que le praticien n'a pas créé le dossier lui-même (spec §58) : un fichier se relit,
se remplace et s'efface d'un geste, et une journée perdue se redemande à l'extension.

Invariant de journalisation (CLAUDE.md) : aucun nom de patient, aucun motif de
rendez-vous ne sort d'ici dans un log. On ne compte que des lignes.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from oris_api.config import Settings

log = logging.getLogger(__name__)

EtatSmileCloud = Literal["trouve", "absent", "a_verifier", "ambigu", "demande", "inconnu"]

#: États que Dental Lens sait produire, si jamais il enrichit la livraison avant de la
#: relayer. L'extension seule n'en envoie pas : tout autre mot devient « inconnu »
#: plutôt que d'être affiché tel quel — un écran ne montre pas un mot qu'il ne comprend pas.
ETATS: frozenset[str] = frozenset({"trouve", "absent", "a_verifier", "ambigu", "demande"})

#: Au-delà, une demande de relecture est oubliée : voir `_vivantes`. Une heure et non
#: douze : une demande que personne n'a servie en une heure ne le sera pas, et laisser
#: l'écran attendre indéfiniment est pire que de lui faire redemander.
DUREE_DEMANDE_MIN = 60

#: On garde une semaine de tentatives de livraison, pas davantage : c'est un fil
#: d'événements, pas un journal.
JOURS_DE_LIVRAISONS = 7


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
    recu_le: str | None
    rendezvous: tuple[RendezVous, ...]

    @property
    def disponible(self) -> bool:
        """Déposée veut dire **relevée dans Doctolib**, pas « la date existe ».

        Sans dépôt, un jeudi jamais relevé s'afficherait comme un jeudi sans patient :
        deux choses très différentes.
        """
        return self.recu_le is not None


@dataclass(frozen=True, slots=True)
class Depot:
    """Ce qu'on répond à l'extension : ce qui a été gardé, et sinon pourquoi."""

    jour: str
    rendezvous: int
    remplace: bool
    raison: str | None = None


class JourneeInvalide(ValueError):
    """Une livraison qu'on ne sait pas ranger : date absente ou illisible."""


def _texte(valeur: object) -> str:
    return valeur.strip() if isinstance(valeur, str) else ""


def _etat(valeur: object) -> EtatSmileCloud:
    mot = _texte(valeur)
    return mot if mot in ETATS else "inconnu"  # type: ignore[return-value]


def _jour_sur(valeur: object) -> str:
    """La date, telle qu'elle servira de **nom de fichier**.

    Elle est refabriquée à partir d'une vraie date : une chaîne venue du dehors ne
    compose jamais un chemin telle quelle, sinon « ../../quelque-chose » écrirait où il
    veut sur le disque.
    """
    try:
        return date.fromisoformat(_texte(valeur)).isoformat()
    except ValueError as erreur:
        raise JourneeInvalide("date du jour absente ou illisible") from erreur


#: Ce que Doctolib met devant le nom, et qui n'en fait pas partie.
CIVILITES: frozenset[str] = frozenset({"M", "Mme", "Mlle", "Mr", "Dr"})


def separer_nom(patient: str) -> tuple[str, str]:
    """« M. DROIT Justine » → (« Justine », « DROIT »). Doctolib écrit le nom en capitales.

    Même règle que Dental Lens (`journee.separer_nom`), pour qu'un patient se coupe de la
    même façon des deux côtés. Tout en capitales ou tout en minuscules : on ne peut pas
    deviner, le premier mot fait le nom.
    """
    mots = [m for m in (patient or "").replace("\xa0", " ").split() if m]
    while mots and mots[0].rstrip(".") in CIVILITES:
        mots.pop(0)
    nom = [m for m in mots if m.isupper() or (len(m) > 1 and m == m.upper())]
    prenom = [m for m in mots if m not in nom]
    if not nom or not prenom:
        nom, prenom = mots[:1], mots[1:]
    return " ".join(prenom), " ".join(nom)


def _rendez_vous(brut: object) -> RendezVous | None:
    """Une ligne d'agenda, ou rien si elle n'a même pas de nom.

    L'extension livre le nom **tel que Doctolib l'écrit**, dans `patient` : « M. DROIT
    Justine ». C'est Dental Lens qui le coupe de son côté, et la note de reprise avait fait
    croire qu'il arrivait déjà coupé. Oris exigeait donc un prénom ou un nom, n'en trouvait
    jamais, et jetait toutes les lignes : chaque journée livrée arrivait vide. On accepte
    donc les deux formes — `prenom`/`nom` s'ils sont là, sinon `patient` coupé ici.

    Un agenda contient aussi des lignes qui ne sont pas des patients (pause, réunion,
    blocage) : sans nom exploitable, la ligne est écartée.
    """
    if not isinstance(brut, dict):
        return None
    prenom, nom = _texte(brut.get("prenom")), _texte(brut.get("nom"))
    if not nom and not prenom:
        prenom, nom = separer_nom(_texte(brut.get("patient")))
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


def _fichier(settings: Settings, jour: str) -> Path:
    return settings.journee_dir / f"{jour}.json"


def _vide(jour: str) -> Journee:
    return Journee(jour=jour, agenda="", recu_le=None, rendezvous=())


def _relire(fichier: Path, jour: str) -> Journee | None:
    try:
        brut = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(brut, dict) or not isinstance(brut.get("rendezvous"), list):
        return None
    return Journee(
        jour=_texte(brut.get("jour")) or jour,
        agenda=_texte(brut.get("agenda")),
        recu_le=_texte(brut.get("recu_le")) or None,
        rendezvous=tuple(filter(None, (_rendez_vous(ligne) for ligne in brut["rendezvous"]))),
    )


def _ecrire(fichier: Path, contenu: dict[str, Any]) -> None:
    """Écriture en deux temps : un fichier complet, ou l'ancien intact.

    Écrire directement dans le fichier final laisserait une journée tronquée si la
    machine s'arrête au milieu — et une journée tronquée est illisible au moment où on
    en a besoin, c'est-à-dire le matin.
    """
    fichier.parent.mkdir(parents=True, exist_ok=True)
    descripteur, provisoire = tempfile.mkstemp(dir=fichier.parent, suffix=".part")
    try:
        with os.fdopen(descripteur, "w", encoding="utf-8") as sortie:
            json.dump(contenu, sortie, ensure_ascii=False, indent=1)
        os.replace(provisoire, fichier)
    except BaseException:
        Path(provisoire).unlink(missing_ok=True)
        raise


def deposer(settings: Settings, livraison: dict[str, Any]) -> Depot:
    """Ranger une journée livrée par l'extension. **N'écrit aucun patient en base.**

    Rejouer une livraison pour la même date remplace la précédente — c'est le cas
    courant : l'agenda bouge dans la journée. Une exception : une livraison vide ne
    remplace jamais une journée qui ne l'était pas. Une lecture ratée (Doctolib lent,
    tableau non compris) renvoie zéro ligne, et elle effacerait la seule liste dont le
    praticien dispose.
    """
    jour = _jour_sur(livraison.get("jour"))
    livrees = livraison.get("rendezvous")
    lignes: tuple[RendezVous, ...] = (
        tuple(filter(None, (_rendez_vous(ligne) for ligne in livrees)))
        if isinstance(livrees, list)
        else ()
    )
    diagnostic = livraison.get("diagnostic")
    comprise = not (isinstance(diagnostic, dict) and diagnostic.get("entetes") is False)

    fichier = _fichier(settings, jour)
    ancienne = _relire(fichier, jour)
    if not lignes and ancienne and ancienne.rendezvous:
        raison = (
            "tableau non compris" if not comprise else "livraison vide"
        ) + " : la journée déjà déposée est conservée"
        log.info(
            "Dépôt %s ignoré (%s) ; %d rendez-vous gardés", jour, raison, len(ancienne.rendezvous)
        )
        refus = Depot(jour=jour, rendezvous=len(ancienne.rendezvous), remplace=False, raison=raison)
        _noter_livraison(settings, refus)
        return refus

    _ecrire(
        fichier,
        {
            "jour": jour,
            "recu_le": datetime.now().astimezone().isoformat(timespec="seconds"),
            "agenda": _texte(livraison.get("agenda")),
            "rendezvous": [
                {
                    "heure": rdv.heure,
                    "prenom": rdv.prenom,
                    "nom": rdv.nom,
                    "motif": rdv.motif,
                    "statut": rdv.statut,
                    "recherche": rdv.smilecloud,
                }
                for rdv in lignes
            ],
        },
    )
    _retirer_demande(settings, jour)
    log.info("Journée %s déposée : %d rendez-vous", jour, len(lignes))
    depot = Depot(jour=jour, rendezvous=len(lignes), remplace=True)
    _noter_livraison(settings, depot)
    return depot


# --- Demander une relecture ---------------------------------------------------------
#
# Oris ne va rien chercher : il ne peut donc pas rafraîchir une journée lui-même. Il
# pose une demande, que l'extension vient lire à son prochain passage et sert en
# déposant la journée. Le praticien clique, l'extension travaille, la journée arrive.


def _fichier_demandes(settings: Settings) -> Path:
    return settings.journee_dir / "demandes.json"


def _lire_demandes(settings: Settings) -> dict[str, str]:
    try:
        brut = json.loads(_fichier_demandes(settings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(brut, dict):
        return {}
    return {str(jour): str(quand) for jour, quand in brut.items() if isinstance(quand, str)}


def _vivantes(demandes: dict[str, str]) -> dict[str, str]:
    """Une demande que personne n'a servie finit par ne plus rien vouloir dire.

    Une demande que personne n'a servie en une heure ne le sera pas : l'extension est
    arrêtée, mal configurée, ou bute sur quelque chose. Mieux vaut que l'écran cesse
    d'attendre et propose de redemander, plutôt qu'il tourne indéfiniment.
    """
    limite = datetime.now().astimezone() - timedelta(minutes=DUREE_DEMANDE_MIN)
    gardees = {}
    for jour, quand in demandes.items():
        try:
            if datetime.fromisoformat(quand) >= limite:
                gardees[jour] = quand
        except ValueError:
            continue
    return gardees


def _ecrire_demandes(settings: Settings, demandes: dict[str, str]) -> None:
    if demandes:
        _ecrire(_fichier_demandes(settings), demandes)
    else:
        _fichier_demandes(settings).unlink(missing_ok=True)


def _retirer_demande(settings: Settings, jour: str) -> None:
    demandes = _vivantes(_lire_demandes(settings))
    if demandes.pop(jour, None) is not None:
        _ecrire_demandes(settings, demandes)


def demander(settings: Settings, jour: str | None = None) -> str:
    """Demander à l'extension de (re)lire cet agenda. Renvoie l'heure de la demande."""
    demande = _jour_sur(jour) if jour else date.today().isoformat()
    quand = datetime.now().astimezone().isoformat(timespec="seconds")
    demandes = _vivantes(_lire_demandes(settings))
    demandes[demande] = quand
    _ecrire_demandes(settings, demandes)
    log.info("Relecture demandée pour la journée %s", demande)
    return quand


def annuler(settings: Settings, jour: str | None = None) -> None:
    """Retirer une demande restée sans réponse. Le praticien ne reste pas coincé."""
    _retirer_demande(settings, _jour_sur(jour) if jour else date.today().isoformat())


def demandes(settings: Settings) -> dict[str, str]:
    """Les jours qu'on attend, du plus ancien au plus récent. Pour l'extension."""
    vivantes = _vivantes(_lire_demandes(settings))
    return dict(sorted(vivantes.items()))


def demande_pour(settings: Settings, jour: str) -> str | None:
    return _vivantes(_lire_demandes(settings)).get(jour)


# --- Ce que l'extension a tenté de livrer -------------------------------------------
#
# Une livraison refusée — une liste vide alors qu'une journée était déjà là — ne se
# voyait nulle part. L'extension réessayait, Oris refusait, et l'écran attendait sans
# que rien ne l'explique. On garde donc la dernière tentative de chaque jour.


def _fichier_livraisons(settings: Settings) -> Path:
    return settings.journee_dir / "livraisons.json"


def _lire_livraisons(settings: Settings) -> dict[str, dict[str, Any]]:
    try:
        brut = json.loads(_fichier_livraisons(settings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return brut if isinstance(brut, dict) else {}


def _noter_livraison(settings: Settings, depot: Depot) -> None:
    livraisons = _lire_livraisons(settings)
    livraisons[depot.jour] = {
        "le": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rendezvous": depot.rendezvous,
        "remplace": depot.remplace,
        "raison": depot.raison,
    }
    vieux = (date.today() - timedelta(days=JOURS_DE_LIVRAISONS)).isoformat()
    gardees = {jour: v for jour, v in livraisons.items() if jour >= vieux}
    _ecrire(_fichier_livraisons(settings), gardees)


def derniere_livraison(settings: Settings, jour: str) -> dict[str, Any] | None:
    tentative = _lire_livraisons(settings).get(jour)
    return tentative if isinstance(tentative, dict) else None


def lire(settings: Settings, jour: str | None = None) -> Journee:
    """La journée demandée, ou une journée vide si personne ne l'a déposée.

    Une journée absente n'est pas une erreur : elle veut dire « l'extension n'a pas
    encore relevé cet agenda ». L'écran le dit, il n'invente pas de rendez-vous.
    """
    try:
        demande = _jour_sur(jour) if jour else date.today().isoformat()
    except JourneeInvalide:
        demande = date.today().isoformat()
    return _relire(_fichier(settings, demande), demande) or _vide(demande)


def lire_semaine(settings: Settings, depuis: str, jours: int = 7) -> list[Journee]:
    """Plusieurs jours d'affilée, pour la colonne de gauche."""
    try:
        premier = date.fromisoformat(depuis)
    except ValueError:
        premier = date.today()
    return [
        lire(settings, (premier + timedelta(days=i)).isoformat())
        for i in range(max(1, min(jours, 31)))
    ]
