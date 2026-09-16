"""Généré par scripts/generate_contracts.py depuis schemas/ — ne pas modifier à la main."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TranscriptSegmentSpeakerRole = Literal["practitioner", "patient", "assistant", "companion", "unknown"]
ClinicalFactCategory = Literal["chief_complaint", "history", "symptom", "clinical_finding", "radiographic_finding", "assessment", "diagnosis", "treatment_option", "treatment_decision", "procedure", "material", "medication", "patient_information", "follow_up", "other"]
ClinicalFactSurfaces = Literal["M", "D", "O", "V", "B", "L", "P", "I", "C"]
ClinicalFactAssertion = Literal["present", "absent", "uncertain"]
ClinicalFactTemporality = Literal["past", "current", "future"]
ClinicalFactClinicalStatus = Literal["patient_reported", "observed", "clinician_assessment", "differential", "discussed", "proposed", "accepted", "refused", "deferred", "planned", "performed"]
ClinicalFactSpeakerRole = Literal["practitioner", "patient", "assistant", "companion", "unknown", "manual"]
ClinicalFactCertainty = Literal["certain", "probable", "possible", "unknown"]
ClinicalFactSourceType = Literal["audio", "manual", "prior_record", "system_test"]
TreatmentPlanStatus = Literal["draft", "review", "validated", "superseded"]
TreatmentPlanItemStatus = Literal["discussed", "proposed", "accepted", "refused", "deferred", "planned", "completed"]
TreatmentPlanItemPriority = Literal["urgent", "high", "routine", "low", "unspecified"]
ProcedureProcedureType = Literal["composite", "direct_aesthetic", "veneer_preparation", "veneer_bonding", "wear_additive", "extraction", "minor_surgery_generic"]
ProcedureStatus = Literal["planned", "performed", "cancelled"]
ClinicalEncounterStatus = Literal["draft", "recording", "paused", "finalizing", "processing", "review", "validated", "exported", "archived", "audio_error", "upload_interrupted", "transcription_failed", "generation_failed"]
EncounterWarningSeverity = Literal["info", "review", "critical"]
DocumentDocumentType = Literal["consultation_note", "treatment_plan_text", "operative_note", "patient_summary", "referral_letter"]
DocumentStatus = Literal["draft_ai", "needs_review", "validated", "exported", "superseded", "outdated"]
LearningEventEventType = Literal["transcript_word_correction", "tooth_number_correction", "speaker_role_correction", "clinical_fact_added", "clinical_fact_removed", "clinical_fact_corrected", "negation_correction", "temporality_correction", "certainty_correction", "treatment_status_correction", "treatment_sequence_correction", "procedure_type_correction", "material_name_correction", "document_text_edit", "document_section_deleted", "document_section_added", "warning_confirmed", "warning_dismissed", "glossary_term_added", "style_preference_detected", "document_validated_unchanged", "document_validated_after_minor_edit", "document_validated_after_major_edit", "generation_rejected"]
LearningEventScope = Literal["user", "organization", "global_candidate"]
LearningEventLearningStatus = Literal["captured", "reviewed", "promoted", "rejected", "purged"]
PractitionerLearningProfilePreferredDocumentLength = Literal["short", "standard", "detailed"]
PractitionerLearningProfilePreferredStyle = Literal["sentences", "semi_telegraphic"]


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str
    start_ms: Annotated[int, Field(ge=0)]
    end_ms: Annotated[int, Field(ge=0)]
    speaker_role: TranscriptSegmentSpeakerRole
    text: str
    confidence: Annotated[float, Field(ge=0, le=1)]
    is_final: bool


class ClinicalFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: Annotated[str, Field(min_length=1)]
    category: ClinicalFactCategory
    concept: Annotated[str, Field(min_length=1)]
    value: Any
    teeth: list[Annotated[str, Field(pattern=r"^(?:1[1-8]|2[1-8]|3[1-8]|4[1-8]|5[1-5]|6[1-5]|7[1-5]|8[1-5])$")]]
    surfaces: list[ClinicalFactSurfaces]
    assertion: ClinicalFactAssertion
    temporality: ClinicalFactTemporality
    clinical_status: ClinicalFactClinicalStatus
    speaker_role: ClinicalFactSpeakerRole
    certainty: ClinicalFactCertainty
    source_type: ClinicalFactSourceType
    evidence_segment_ids: list[str]
    confidence: Annotated[float, Field(ge=0, le=1)]
    manually_validated: bool


class TreatmentPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    teeth: list[str]
    problem: str | None
    action: str
    status: TreatmentPlanItemStatus
    priority: TreatmentPlanItemPriority
    sequence: Annotated[int, Field(ge=1)] | None
    alternatives: list[str]
    prerequisites: list[str]
    uncertainties: list[str]
    evidence_fact_ids: list[str]


class TreatmentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    status: TreatmentPlanStatus
    goals: list[str]
    notes: list[str]
    items: list[TreatmentPlanItem]


class Procedure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    procedure_id: str
    procedure_type: ProcedureProcedureType
    status: ProcedureStatus
    teeth: list[str]
    structured_data: dict[str, Any]
    evidence_fact_ids: list[str]


class EncounterWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: EncounterWarningSeverity
    message: str


class ClinicalEncounter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encounter_id: str
    patient_id: str
    practitioner_id: str
    started_at: str
    ended_at: str | None
    status: ClinicalEncounterStatus
    object_version: Annotated[int, Field(ge=1)]
    facts: list[ClinicalFact]
    treatment_plan: TreatmentPlan | None
    procedures: list[Procedure]
    warnings: list[EncounterWarning]


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: DocumentDocumentType
    status: DocumentStatus
    encounter_object_version: Annotated[int, Field(ge=1)]
    content: str
    supported_fact_ids: list[str]


class LearningEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learning_event_id: str
    organization_id: str
    user_id: str
    encounter_id: str
    event_type: LearningEventEventType
    scope: LearningEventScope
    source_version: str
    before: Any
    after: Any
    reason: str | None = None
    confidence_before: Annotated[float, Field(ge=0, le=1)] | None = None
    validated_by_practitioner: bool
    created_at: str
    eligible_for_global_learning: bool
    learning_status: LearningEventLearningStatus


class SpeechAlias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heard: str
    canonical: str


class PractitionerLearningProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    preferred_document_length: PractitionerLearningProfilePreferredDocumentLength
    preferred_style: PractitionerLearningProfilePreferredStyle
    preferred_terms: dict[str, str]
    frequent_materials: list[str]
    speech_aliases: list[SpeechAlias]
    document_preferences: dict[str, Any]
    last_updated_at: str


class EvaluationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_run_id: str
    component: str
    candidate_version: str
    dataset_version: str
    metrics: dict[str, float]
    critical_regressions: list[str]
    created_at: str
    release_gate_passed: bool
