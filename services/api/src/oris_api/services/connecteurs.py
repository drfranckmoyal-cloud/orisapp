"""État de Doctolib et de SmileCloud, lu chez Dental Lens.

Oris ne parle ni à Doctolib ni à SmileCloud : c'est l'extension Chrome de Dental Lens qui
le fait, et le serveur de Dental Lens (sur ce Mac, 127.0.0.1:8765) sait où elle en est.
Oris lui demande, et traduit en voyants — les mêmes mots que Dental Lens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

DENTAL_LENS = "http://127.0.0.1:8765"
DELAI_S = 1.5


def _heure(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%H:%M")
    except ValueError:
        return ""


def _jour(iso: str | None) -> str:
    """« 2026-10-09 » -> « 09/10 »."""
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m")
    except ValueError:
        return str(iso or "")


def lire_etat_dental_lens(client: httpx.Client | None = None) -> dict[str, Any] | None:
    """La santé de Dental Lens, ou None s'il ne répond pas."""
    try:
        http = client or httpx.Client(timeout=DELAI_S)
        try:
            reponse = http.get(f"{DENTAL_LENS}/api/etat")
        finally:
            if client is None:
                http.close()
        if reponse.status_code != 200:
            return None
        corps = reponse.json()
        return corps.get("sante") if isinstance(corps, dict) else None
    except (httpx.HTTPError, ValueError):
        return None


def voyants(sante: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Doctolib et SmileCloud en voyants : état court, ton, détail, et le site à ouvrir
    quand un geste le règle (reconnecter)."""
    if sante is None:
        inconnu = {
            "etat": "inconnu",
            "ton": "neutre",
            "detail": "Dental Lens ne répond pas sur ce Mac : état inconnu.",
            "ouvrir": None,
        }
        return {"doctolib": dict(inconnu), "smilecloud": dict(inconnu)}

    extension = sante.get("extension") or {}
    active = bool(sante.get("extension_active"))
    chrome_absent: dict[str, Any] = {
        "etat": "Chrome fermé",
        "ton": "alerte",
        "detail": (
            "L'extension de Dental Lens ne donne plus signe de vie : Chrome est peut-être fermé."
        ),
    }

    # Doctolib
    doc = sante.get("doctolib") or {}
    derniere = doc.get("derniere_lecture") or {}
    rappel = (
        f"Agenda du {_jour(derniere.get('jour'))} lu à {_heure(derniere.get('lu_le'))} : "
        f"{derniere.get('rendezvous', 0)} rendez-vous."
        if derniere
        else "Aucun agenda lu pour l'instant."
    )
    doctolib: dict[str, Any]
    smilecloud: dict[str, Any]
    if not active:
        doctolib = {**chrome_absent, "ouvrir": "doctolib"}
    elif doc.get("etat") == "lecture":
        doctolib = {"etat": "lecture en cours", "ton": "travail", "detail": rappel, "ouvrir": None}
    elif doc.get("etat") == "connexion":
        doctolib = {
            "etat": "à reconnecter",
            "ton": "alerte",
            "detail": "Doctolib demande une connexion dans Chrome. " + rappel,
            "ouvrir": "doctolib",
        }
    elif doc.get("etat") == "ok" or doc.get("ouvert"):
        doctolib = {"etat": "ouvert", "ton": "actif", "detail": rappel, "ouvrir": None}
    else:
        doctolib = {
            "etat": "fermé",
            "ton": "neutre",
            "detail": "Aucun onglet Doctolib dans Chrome. " + rappel,
            "ouvrir": "doctolib",
        }

    # SmileCloud
    if not active:
        smilecloud = {**chrome_absent, "ouvrir": "smilecloud"}
    elif extension.get("session") == "ok":
        smilecloud = {
            "etat": "connecté",
            "ton": "actif",
            "detail": "Session confirmée par une page SmileCloud.",
            "ouvrir": None,
        }
    elif extension.get("session") == "expiree":
        smilecloud = {
            "etat": "à reconnecter",
            "ton": "alerte",
            "detail": "SmileCloud vous a déconnecté : reconnectez-vous dans Chrome.",
            "ouvrir": "smilecloud",
        }
    elif sante.get("smilecloud_ouvert"):
        smilecloud = {
            "etat": "ouvert",
            "ton": "actif",
            "detail": "Un onglet SmileCloud est ouvert dans Chrome.",
            "ouvrir": None,
        }
    else:
        smilecloud = {
            "etat": "fermé",
            "ton": "neutre",
            "detail": "Aucun onglet SmileCloud dans Chrome.",
            "ouvrir": "smilecloud",
        }
    # Oris ne se sert pas encore de SmileCloud : on le dit, pour ne rien promettre.
    smilecloud["detail"] += " Oris ne s'en sert pas encore."
    return {"doctolib": doctolib, "smilecloud": smilecloud}


def ouvrir(site: str, client: httpx.Client | None = None) -> bool:
    """Demande à Dental Lens d'ouvrir Doctolib ou SmileCloud dans Chrome, sur ce Mac."""
    try:
        http = client or httpx.Client(timeout=4)
        try:
            reponse = http.post(f"{DENTAL_LENS}/api/ouvrir-site", json={"site": site})
        finally:
            if client is None:
                http.close()
        return reponse.status_code == 200
    except httpx.HTTPError:
        return False
