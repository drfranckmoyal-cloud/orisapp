"""Déballage d'une sortie d'outil doublement encodée.

Le 09/10/2026, l'attribution des voix d'une consultation de trente-trois minutes a été
refusée alors que le modèle avait juste : il avait rendu tout son objet **dans une
chaîne de caractères**, à la place de la liste attendue —
`{"voix": "{\\"voix\\": [{\\"label\\": \\"0\\", \\"role\\": \\"practitioner\\"}]}"}`.
La réponse était bonne, l'emballage faux, et les 250 passages sont restés « locuteur
inconnu », ce qui a fait échouer l'extraction entière.

Déballer n'est pas rafistoler : rien n'est ajouté, rien n'est corrigé, rien n'est
devenu plus certain. Ce qui ne se déballe pas proprement reste refusé comme avant.
"""

from __future__ import annotations

import json
from typing import Any


def deballer(raw: dict[str, Any]) -> dict[str, Any]:
    """La sortie d'outil, débarrassée d'un encodage en trop s'il y en a un."""
    for cle, valeur in raw.items():
        if not isinstance(valeur, str):
            continue
        try:
            dedans = json.loads(valeur)
        except ValueError:
            continue
        # Tout l'objet était dans la chaîne : c'est lui la vraie sortie.
        if isinstance(dedans, dict) and cle in dedans:
            return dedans
        # Seule la liste était encodée : on remet la liste à sa place.
        if isinstance(dedans, list):
            return {**raw, cle: dedans}
    return raw
