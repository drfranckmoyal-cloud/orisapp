"""Veasy (Visiodent) : déposer un document d'Oris dans le dossier du patient.

Franck, le 25/11/2026 : « il faut qu'Oris puisse déposer directement le compte rendu dans
le dossier Veasy du patient, il est connecté sur le navigateur ». Même chemin que
SmileCloud : Oris ne touche pas à Veasy, il pose une demande ; l'extension Chrome de
Dental Lens, qui tourne dans la session Veasy du praticien, vient la chercher, retire le
PDF, le dépose, et dit ce qu'il en est. Contrat : `docs/DEPOT_VEASY.md`.

Rien n'est gardé ici que la file des demandes : ni PDF, ni texte clinique.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from oris_api.config import Settings

#: Une demande que personne n'a servie en un jour ne le sera plus : on l'oublie, et le
#: praticien la redemande. Douze heures, c'était trop court pour une demande du soir.
DUREE_DEMANDE = timedelta(hours=24)


def _fichier(settings: Settings) -> Path:
    settings.veasy_dir.mkdir(parents=True, exist_ok=True)
    return settings.veasy_dir / "demandes.json"


def _maintenant() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _lire(settings: Settings) -> list[dict[str, Any]]:
    try:
        brut = json.loads(_fichier(settings).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [d for d in brut if isinstance(d, dict)] if isinstance(brut, list) else []


def _ecrire(settings: Settings, demandes: list[dict[str, Any]]) -> None:
    fichier = _fichier(settings)
    # Écriture d'un bloc : un fichier à moitié écrit perdrait toute la file.
    descripteur, temporaire = tempfile.mkstemp(dir=fichier.parent, suffix=".tmp")
    with os.fdopen(descripteur, "w", encoding="utf-8") as sortie:
        json.dump(demandes[-50:], sortie, ensure_ascii=False)
    os.chmod(temporaire, 0o600)
    os.replace(temporaire, fichier)


def _vivantes(demandes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    limite = datetime.now(UTC) - DUREE_DEMANDE
    return [
        d for d in demandes if d.get("termine") or datetime.fromisoformat(d["demande_le"]) > limite
    ]


def demander_depot(
    settings: Settings,
    *,
    document_id: UUID,
    nom_fichier: str,
    patient: dict[str, str],
    patient_id: UUID,
    organisation_id: UUID,
    praticien_id: UUID,
) -> dict[str, Any]:
    """Une demande ouverte par document : redemander ne fait pas deux dépôts."""
    demandes = _vivantes(_lire(settings))
    for d in demandes:
        if d.get("document_id") == str(document_id) and not d.get("termine"):
            return d
    demande = {
        "id": uuid4().hex,
        "document_id": str(document_id),
        "nom_fichier": nom_fichier,
        "patient": patient,
        # Pour apprendre le numéro Veasy au retour ; jamais servi à l'extension.
        "patient_id": str(patient_id),
        "organisation_id": str(organisation_id),
        "praticien_id": str(praticien_id),
        "demande_le": _maintenant(),
    }
    demandes.append(demande)
    _ecrire(settings, demandes)
    return demande


def demande(settings: Settings, demande_id: str) -> dict[str, Any] | None:
    return next((d for d in _lire(settings) if d.get("id") == demande_id), None)


def en_attente(settings: Settings) -> list[dict[str, Any]]:
    """Ce que l'extension doit faire, sans rien d'autre que ce dont elle a besoin."""
    return [
        {
            "id": d["id"],
            "document_id": d["document_id"],
            "nom_fichier": d["nom_fichier"],
            "patient": d["patient"],
            "demande_le": d["demande_le"],
            "essais": int(d.get("essais", 0)),
        }
        for d in _vivantes(_lire(settings))
        if not d.get("termine")
    ]


def noter(
    settings: Settings,
    demande_id: str,
    *,
    raison: str = "",
    reessayer: bool = False,
    veasy_patient_id: str = "",
) -> dict[str, Any] | None:
    """L'extension a déposé le document — ou dit pourquoi non.

    `reessayer` : rien n'est parti et ça vaut la peine de recommencer (page pas prête) ;
    la demande reste ouverte. Sinon elle se ferme, déposée ou impossible.
    """
    demandes = _lire(settings)
    for d in demandes:
        if d.get("id") != demande_id:
            continue
        d["depose_le"] = _maintenant()
        if raison:
            d["raison"] = raison
        else:
            d.pop("raison", None)
        if veasy_patient_id:
            d["veasy_patient_id"] = veasy_patient_id
        if reessayer and raison:
            d["essais"] = int(d.get("essais", 0)) + 1
        else:
            d["termine"] = True
        _ecrire(settings, demandes)
        return d
    return None


def dernier_depot(settings: Settings, document_id: UUID) -> dict[str, Any] | None:
    for d in reversed(_vivantes(_lire(settings))):
        if d.get("document_id") == str(document_id):
            return d
    return None
