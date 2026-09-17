"""Alertes déterministes d'une consultation (spec §25 étape 8, §31)."""

from __future__ import annotations

from oris_api.contracts import EncounterWarning
from oris_api.domain.types import AudioGap

AUDIO_GAP = "AUDIO_GAP"
AUDIO_GAP_MESSAGE = "Une portion significative de la consultation n’a pas été captée."


def compute_warnings(gaps: list[AudioGap]) -> list[EncounterWarning]:
    """Un trou audio non récupéré est toujours critique (test J) : il interdit de
    présenter le compte rendu comme exhaustif."""
    warnings: list[EncounterWarning] = []
    if gaps:
        warnings.append(
            EncounterWarning(code=AUDIO_GAP, severity="critical", message=AUDIO_GAP_MESSAGE)
        )
    return warnings
