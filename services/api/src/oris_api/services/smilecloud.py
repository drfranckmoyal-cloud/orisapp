"""SmileCloud : relier un patient à son dossier, lire ses galeries, en rapatrier des fichiers.

Oris ne parle pas à SmileCloud. C'est l'extension Chrome (dépôt `smilecloud-photos`) qui,
dans la session de Franck, lit ce que le site affiche et le livre ici — comme elle livre
déjà la journée Doctolib. Oris pose des **demandes** ; l'extension les lit, fait le travail
dans SmileCloud, et rend le résultat. Contrat : `docs/PIECES_JOINTES_SMILECLOUD.md`.

Tout est rangé hors de la base clinique et hors iCloud (`smilecloud_dir`) : la liste des
dossiers et les galeries sont des noms et des dates, pas des faits cliniques. Les fichiers
rapatriés, eux, entrent par la porte des pièces jointes (empreinte, doublons refusés).
Aucun nom de patient ni de galerie ne passe dans les journaux techniques.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from oris_api.config import Settings
from oris_api.services import rapprochement

MOTIF_CASE_ID = re.compile(r"^[0-9a-fA-F-]{8,64}$")
#: Ce qui ne se rapatrie pas (arbitrage de Franck) : trop lourd, rien à faire dans un CR.
NATURES_EXCLUES = frozenset({"video", "cbct"})
NATURES = frozenset({"photo", "radio", "scan3d", "pdf", "video", "cbct", "autre"})
#: Une demande que l'extension n'a pas servie en douze heures est oubliée.
DUREE_DEMANDE = timedelta(hours=12)


class SmileCloudInvalide(ValueError):
    pass


# --- Rangement ------------------------------------------------------------------------


def _dossier(settings: Settings) -> Path:
    racine = Path(settings.smilecloud_dir)
    (racine / "galeries").mkdir(parents=True, exist_ok=True)
    return racine


def _lire(chemin: Path, defaut: Any) -> Any:
    try:
        return json.loads(chemin.read_text())
    except (OSError, json.JSONDecodeError):
        return defaut


def _ecrire(chemin: Path, contenu: Any) -> None:
    """En deux temps : un fichier complet, ou l'ancien intact."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd, provisoire = tempfile.mkstemp(dir=chemin.parent, prefix=".ecriture-")
    with os.fdopen(fd, "w") as f:
        json.dump(contenu, f, ensure_ascii=False)
    os.chmod(provisoire, 0o600)
    os.replace(provisoire, chemin)


def _maintenant() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- Liste des dossiers SmileCloud --------------------------------------------------------


def deposer_dossiers(settings: Settings, dossiers: list[dict[str, Any]]) -> int:
    """La liste des dossiers vue dans SmileCloud par l'extension. Remplace la précédente."""
    propres = []
    for d in dossiers:
        nom = " ".join(str(d.get("nom", "")).split())
        case_id = str(d.get("case_id", ""))
        if nom and MOTIF_CASE_ID.match(case_id):
            propres.append({"case_id": case_id, "nom": nom})
    if dossiers and not propres:
        raise SmileCloudInvalide("aucun dossier reconnu")
    _ecrire(_dossier(settings) / "dossiers.json", {"le": _maintenant(), "dossiers": propres})
    return len(propres)


def dossiers(settings: Settings) -> list[dict[str, str]]:
    return list(_lire(_dossier(settings) / "dossiers.json", {}).get("dossiers", []))


def nom_du_dossier(settings: Settings, case_id: str) -> str | None:
    return next((d["nom"] for d in dossiers(settings) if d["case_id"] == case_id), None)


def proposer(settings: Settings, nom_patient: str) -> rapprochement.Proposition:
    """Les dossiers SmileCloud qui pourraient être ceux de ce patient, avec leur %."""
    return rapprochement.proposer(
        nom_patient, ((d["case_id"], d["nom"]) for d in dossiers(settings))
    )


# --- Demandes (lues par l'extension) ------------------------------------------------------


def _demandes(settings: Settings) -> list[dict[str, Any]]:
    toutes = list(_lire(_dossier(settings) / "demandes.json", []))
    limite = datetime.now(UTC) - DUREE_DEMANDE
    return [
        d for d in toutes if d.get("termine") or datetime.fromisoformat(d["demande_le"]) > limite
    ]


def _ranger_demandes(settings: Settings, demandes: list[dict[str, Any]]) -> None:
    # On garde les 50 dernières : assez pour suivre, pas une archive.
    _ecrire(_dossier(settings) / "demandes.json", demandes[-50:])


def demander_galeries(settings: Settings, case_id: str) -> dict[str, Any]:
    """Relire les galeries d'un dossier. Une seule demande en attente par dossier."""
    demandes = _demandes(settings)
    for d in demandes:
        if d["type"] == "galeries" and d["case_id"] == case_id and not d.get("termine"):
            return d
    demande = {
        "id": uuid4().hex,
        "type": "galeries",
        "case_id": case_id,
        "demande_le": _maintenant(),
    }
    demandes.append(demande)
    _ranger_demandes(settings, demandes)
    return demande


def demander_fichiers(
    settings: Settings,
    case_id: str,
    patient_id: UUID,
    organisation_id: UUID,
    praticien_id: UUID,
    res_ids: list[str],
) -> dict[str, Any]:
    """Rapatrier ces fichiers dans le dossier du patient. Vidéos et CBCT sont écartés ici,
    sans même être demandés à l'extension."""
    galeries = lire_galeries(settings, case_id) or {"galeries": []}
    connus = {f["res_id"]: f for g in galeries["galeries"] for f in g["fichiers"]}
    voulus, ecartes = [], []
    for res_id in dict.fromkeys(res_ids):
        fichier = connus.get(res_id)
        if fichier is None:
            ecartes.append({"res_id": res_id, "raison": "inconnu"})
        elif fichier["nature"] in NATURES_EXCLUES:
            ecartes.append({"res_id": res_id, "raison": fichier["nature"]})
        else:
            voulus.append({"res_id": res_id, "galerie": fichier.get("galerie", "")})
    demande = {
        "id": uuid4().hex,
        "type": "fichiers",
        "case_id": case_id,
        "patient_id": str(patient_id),
        "organisation_id": str(organisation_id),
        "praticien_id": str(praticien_id),
        "fichiers": voulus,
        "recus": [],
        "ecartes": ecartes,
        "demande_le": _maintenant(),
        "termine": not voulus,
    }
    demandes = _demandes(settings)
    demandes.append(demande)
    _ranger_demandes(settings, demandes)
    return demande


def demandes_en_attente(settings: Settings) -> list[dict[str, Any]]:
    """Ce que l'extension doit faire, sans rien d'autre que ce dont elle a besoin."""
    return [
        {
            "id": d["id"],
            "type": d["type"],
            "case_id": d["case_id"],
            "demande_le": d["demande_le"],
            **(
                {"fichiers": [f["res_id"] for f in d["fichiers"] if f["res_id"] not in d["recus"]]}
                if d["type"] == "fichiers"
                else {}
            ),
        }
        for d in _demandes(settings)
        if not d.get("termine")
    ]


def demande(settings: Settings, demande_id: str) -> dict[str, Any] | None:
    return next((d for d in _demandes(settings) if d["id"] == demande_id), None)


def derniere_recuperation(settings: Settings, patient_id: UUID) -> dict[str, Any] | None:
    pour_lui = [
        d
        for d in _demandes(settings)
        if d["type"] == "fichiers" and d.get("patient_id") == str(patient_id)
    ]
    return pour_lui[-1] if pour_lui else None


def galeries_en_attente(settings: Settings, case_id: str) -> bool:
    return any(
        d["type"] == "galeries" and d["case_id"] == case_id and not d.get("termine")
        for d in _demandes(settings)
    )


def _modifier(settings: Settings, demande_id: str, changer: Any) -> dict[str, Any]:
    demandes = _demandes(settings)
    for d in demandes:
        if d["id"] == demande_id:
            changer(d)
            _ranger_demandes(settings, demandes)
            return d
    raise SmileCloudInvalide("demande inconnue")


# --- Galeries (livrées par l'extension) ----------------------------------------------------


def deposer_galeries(settings: Settings, case_id: str, galeries: list[dict[str, Any]]) -> int:
    """Les galeries d'un dossier, telles que SmileCloud les affiche. Sert la demande."""
    if not MOTIF_CASE_ID.match(case_id):
        raise SmileCloudInvalide("dossier SmileCloud illisible")
    propres = []
    for g in galeries:
        fichiers = []
        for f in g.get("fichiers") or []:
            res_id = str(f.get("res_id", ""))
            if not MOTIF_CASE_ID.match(res_id):
                continue
            nature = str(f.get("nature", "autre"))
            fichiers.append(
                {
                    "res_id": res_id,
                    "nom": str(f.get("nom", ""))[:200],
                    "nature": nature if nature in NATURES else "autre",
                    "galerie": str(g.get("nom", ""))[:200],
                }
            )
        propres.append(
            {
                "id": str(g.get("id", ""))[:80],
                "nom": str(g.get("nom", ""))[:200],
                "date": str(g.get("date", ""))[:40],
                "fichiers": fichiers,
            }
        )
    _ecrire(
        _dossier(settings) / "galeries" / f"{case_id}.json",
        {"case_id": case_id, "lu_le": _maintenant(), "galeries": propres},
    )
    demandes = _demandes(settings)
    for d in demandes:
        if d["type"] == "galeries" and d["case_id"] == case_id:
            d["termine"] = True
    _ranger_demandes(settings, demandes)
    return len(propres)


def lire_galeries(settings: Settings, case_id: str) -> dict[str, Any] | None:
    if not MOTIF_CASE_ID.match(case_id):
        return None
    contenu = _lire(_dossier(settings) / "galeries" / f"{case_id}.json", None)
    return contenu if isinstance(contenu, dict) else None


# --- Fichiers (poussés un par un par l'extension) ------------------------------------------


def noter_recu(settings: Settings, demande_id: str, res_id: str) -> dict[str, Any]:
    def changer(d: dict[str, Any]) -> None:
        if res_id not in d["recus"]:
            d["recus"].append(res_id)
        d["termine"] = len(d["recus"]) + len(d["ecartes"]) >= len(
            d["fichiers"]
        ) + _ecartes_d_office(d)

    return _modifier(settings, demande_id, changer)


def noter_ecarte(settings: Settings, demande_id: str, res_id: str, raison: str) -> dict[str, Any]:
    def changer(d: dict[str, Any]) -> None:
        if all(e["res_id"] != res_id for e in d["ecartes"]):
            d["ecartes"].append({"res_id": res_id, "raison": raison[:80]})
        d["termine"] = len(d["recus"]) + len(d["ecartes"]) >= len(
            d["fichiers"]
        ) + _ecartes_d_office(d)

    return _modifier(settings, demande_id, changer)


def _ecartes_d_office(d: dict[str, Any]) -> int:
    """Les écartés avant même d'être demandés (vidéos, CBCT) comptent déjà comme traités."""
    demandes = {f["res_id"] for f in d["fichiers"]}
    return sum(1 for e in d["ecartes"] if e["res_id"] not in demandes)
