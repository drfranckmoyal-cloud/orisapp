"""Alertes déterministes d'une consultation (spec §25 étape 8, §31)."""

from __future__ import annotations

from oris_api.contracts import EncounterWarning, TranscriptSegment
from oris_api.domain.resolver import is_gap_marker
from oris_api.domain.types import AudioGap

AUDIO_GAP = "AUDIO_GAP"
AUDIO_GAP_MESSAGE = "Une portion significative de la consultation n’a pas été captée."
SPEAKER_ROLES_UNKNOWN = "SPEAKER_ROLES_UNKNOWN"
SPEAKER_ROLES_UNKNOWN_MESSAGE = (
    "Les voix n’ont pas pu être attribuées avec certitude : vérifiez ce qui vient "
    "du patient et ce qui vient du praticien."
)


def compute_warnings(
    gaps: list[AudioGap], segments: list[TranscriptSegment] | None = None
) -> list[EncounterWarning]:
    """Un trou audio non récupéré est toujours critique (test J) : il interdit de
    présenter le compte rendu comme exhaustif.

    Un locuteur non identifié n'est pas critique mais doit être vu : sans rôle sûr,
    rien ne garantit qu'une impression du patient n'a pas été écrite comme un constat
    du praticien (invariant 5).
    """
    warnings: list[EncounterWarning] = []
    if gaps:
        warnings.append(
            EncounterWarning(code=AUDIO_GAP, severity="critical", message=AUDIO_GAP_MESSAGE)
        )
    spoken = [s for s in (segments or []) if not is_gap_marker(s)]
    if spoken and any(s.speaker_role == "unknown" for s in spoken):
        warnings.append(
            EncounterWarning(
                code=SPEAKER_ROLES_UNKNOWN,
                severity="review",
                message=SPEAKER_ROLES_UNKNOWN_MESSAGE,
            )
        )
    return warnings
