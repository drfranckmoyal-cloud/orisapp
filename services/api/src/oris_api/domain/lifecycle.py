"""Machine à états d'une consultation (spec §49).

draft → recording ↔ paused → finalizing → processing → review → validated →
exported → archived. Les erreurs sont récupérables sans dupliquer la consultation.
"""

from __future__ import annotations

from oris_api.contracts.generated import ClinicalEncounterStatus

TRANSITIONS: dict[ClinicalEncounterStatus, frozenset[ClinicalEncounterStatus]] = {
    "draft": frozenset({"recording"}),
    "recording": frozenset({"paused", "finalizing", "audio_error", "upload_interrupted"}),
    "paused": frozenset({"recording", "finalizing", "audio_error", "upload_interrupted"}),
    "finalizing": frozenset({"processing", "transcription_failed"}),
    "processing": frozenset({"review", "transcription_failed", "generation_failed"}),
    # Une correction après validation rouvre la révision.
    "review": frozenset({"validated"}),
    "validated": frozenset({"review", "exported", "archived"}),
    "exported": frozenset({"review", "archived"}),
    "archived": frozenset(),
    # Reprises après erreur.
    "audio_error": frozenset({"recording", "finalizing"}),
    "upload_interrupted": frozenset({"recording", "finalizing"}),
    "transcription_failed": frozenset({"processing"}),
    "generation_failed": frozenset({"processing"}),
}


class TransitionError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"{current} -> {target}")


def ensure_transition(current: str, target: ClinicalEncounterStatus) -> ClinicalEncounterStatus:
    allowed = TRANSITIONS.get(current, frozenset())  # type: ignore[call-overload]
    if target not in allowed:
        raise TransitionError(current, target)
    return target
