"""Contrats cliniques : types générés depuis `schemas/` et validation normative."""

from oris_api.contracts.generated import (
    ClinicalEncounter,
    ClinicalFact,
    Document,
    EncounterWarning,
    LearningEvent,
    Procedure,
    TranscriptSegment,
    TreatmentPlan,
    TreatmentPlanItem,
)
from oris_api.contracts.validation import ContractViolation, validate_contract

__all__ = [
    "ClinicalEncounter",
    "ClinicalFact",
    "ContractViolation",
    "Document",
    "EncounterWarning",
    "LearningEvent",
    "Procedure",
    "TranscriptSegment",
    "TreatmentPlan",
    "TreatmentPlanItem",
    "validate_contract",
]
