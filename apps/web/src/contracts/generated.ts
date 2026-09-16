// Généré par scripts/generate_contracts.py depuis schemas/ — ne pas modifier à la main.

export const TRANSCRIPT_SEGMENT_SPEAKER_ROLE_VALUES = [
  "practitioner",
  "patient",
  "assistant",
  "companion",
  "unknown",
] as const;
export type TranscriptSegmentSpeakerRole = (typeof TRANSCRIPT_SEGMENT_SPEAKER_ROLE_VALUES)[number];

export const CLINICAL_FACT_CATEGORY_VALUES = [
  "chief_complaint",
  "history",
  "symptom",
  "clinical_finding",
  "radiographic_finding",
  "assessment",
  "diagnosis",
  "treatment_option",
  "treatment_decision",
  "procedure",
  "material",
  "medication",
  "patient_information",
  "follow_up",
  "other",
] as const;
export type ClinicalFactCategory = (typeof CLINICAL_FACT_CATEGORY_VALUES)[number];

export const CLINICAL_FACT_SURFACES_VALUES = [
  "M",
  "D",
  "O",
  "V",
  "B",
  "L",
  "P",
  "I",
  "C",
] as const;
export type ClinicalFactSurfaces = (typeof CLINICAL_FACT_SURFACES_VALUES)[number];

export const CLINICAL_FACT_ASSERTION_VALUES = [
  "present",
  "absent",
  "uncertain",
] as const;
export type ClinicalFactAssertion = (typeof CLINICAL_FACT_ASSERTION_VALUES)[number];

export const CLINICAL_FACT_TEMPORALITY_VALUES = [
  "past",
  "current",
  "future",
] as const;
export type ClinicalFactTemporality = (typeof CLINICAL_FACT_TEMPORALITY_VALUES)[number];

export const CLINICAL_FACT_CLINICAL_STATUS_VALUES = [
  "patient_reported",
  "observed",
  "clinician_assessment",
  "differential",
  "discussed",
  "proposed",
  "accepted",
  "refused",
  "deferred",
  "planned",
  "performed",
] as const;
export type ClinicalFactClinicalStatus = (typeof CLINICAL_FACT_CLINICAL_STATUS_VALUES)[number];

export const CLINICAL_FACT_SPEAKER_ROLE_VALUES = [
  "practitioner",
  "patient",
  "assistant",
  "companion",
  "unknown",
  "manual",
] as const;
export type ClinicalFactSpeakerRole = (typeof CLINICAL_FACT_SPEAKER_ROLE_VALUES)[number];

export const CLINICAL_FACT_CERTAINTY_VALUES = [
  "certain",
  "probable",
  "possible",
  "unknown",
] as const;
export type ClinicalFactCertainty = (typeof CLINICAL_FACT_CERTAINTY_VALUES)[number];

export const CLINICAL_FACT_SOURCE_TYPE_VALUES = [
  "audio",
  "manual",
  "prior_record",
  "system_test",
] as const;
export type ClinicalFactSourceType = (typeof CLINICAL_FACT_SOURCE_TYPE_VALUES)[number];

export const TREATMENT_PLAN_STATUS_VALUES = [
  "draft",
  "review",
  "validated",
  "superseded",
] as const;
export type TreatmentPlanStatus = (typeof TREATMENT_PLAN_STATUS_VALUES)[number];

export const TREATMENT_PLAN_ITEM_STATUS_VALUES = [
  "discussed",
  "proposed",
  "accepted",
  "refused",
  "deferred",
  "planned",
  "completed",
] as const;
export type TreatmentPlanItemStatus = (typeof TREATMENT_PLAN_ITEM_STATUS_VALUES)[number];

export const TREATMENT_PLAN_ITEM_PRIORITY_VALUES = [
  "urgent",
  "high",
  "routine",
  "low",
  "unspecified",
] as const;
export type TreatmentPlanItemPriority = (typeof TREATMENT_PLAN_ITEM_PRIORITY_VALUES)[number];

export const PROCEDURE_PROCEDURE_TYPE_VALUES = [
  "composite",
  "direct_aesthetic",
  "veneer_preparation",
  "veneer_bonding",
  "wear_additive",
  "extraction",
  "minor_surgery_generic",
] as const;
export type ProcedureProcedureType = (typeof PROCEDURE_PROCEDURE_TYPE_VALUES)[number];

export const PROCEDURE_STATUS_VALUES = [
  "planned",
  "performed",
  "cancelled",
] as const;
export type ProcedureStatus = (typeof PROCEDURE_STATUS_VALUES)[number];

export const CLINICAL_ENCOUNTER_STATUS_VALUES = [
  "draft",
  "recording",
  "paused",
  "finalizing",
  "processing",
  "review",
  "validated",
  "exported",
  "archived",
  "audio_error",
  "upload_interrupted",
  "transcription_failed",
  "generation_failed",
] as const;
export type ClinicalEncounterStatus = (typeof CLINICAL_ENCOUNTER_STATUS_VALUES)[number];

export const ENCOUNTER_WARNING_SEVERITY_VALUES = [
  "info",
  "review",
  "critical",
] as const;
export type EncounterWarningSeverity = (typeof ENCOUNTER_WARNING_SEVERITY_VALUES)[number];

export const DOCUMENT_DOCUMENT_TYPE_VALUES = [
  "consultation_note",
  "treatment_plan_text",
  "operative_note",
  "patient_summary",
  "referral_letter",
] as const;
export type DocumentDocumentType = (typeof DOCUMENT_DOCUMENT_TYPE_VALUES)[number];

export const DOCUMENT_STATUS_VALUES = [
  "draft_ai",
  "needs_review",
  "validated",
  "exported",
  "superseded",
  "outdated",
] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUS_VALUES)[number];

export const LEARNING_EVENT_EVENT_TYPE_VALUES = [
  "transcript_word_correction",
  "tooth_number_correction",
  "speaker_role_correction",
  "clinical_fact_added",
  "clinical_fact_removed",
  "clinical_fact_corrected",
  "negation_correction",
  "temporality_correction",
  "certainty_correction",
  "treatment_status_correction",
  "treatment_sequence_correction",
  "procedure_type_correction",
  "material_name_correction",
  "document_text_edit",
  "document_section_deleted",
  "document_section_added",
  "warning_confirmed",
  "warning_dismissed",
  "glossary_term_added",
  "style_preference_detected",
  "document_validated_unchanged",
  "document_validated_after_minor_edit",
  "document_validated_after_major_edit",
  "generation_rejected",
] as const;
export type LearningEventEventType = (typeof LEARNING_EVENT_EVENT_TYPE_VALUES)[number];

export const LEARNING_EVENT_SCOPE_VALUES = [
  "user",
  "organization",
  "global_candidate",
] as const;
export type LearningEventScope = (typeof LEARNING_EVENT_SCOPE_VALUES)[number];

export const LEARNING_EVENT_LEARNING_STATUS_VALUES = [
  "captured",
  "reviewed",
  "promoted",
  "rejected",
  "purged",
] as const;
export type LearningEventLearningStatus = (typeof LEARNING_EVENT_LEARNING_STATUS_VALUES)[number];

export const PRACTITIONER_LEARNING_PROFILE_PREFERRED_DOCUMENT_LENGTH_VALUES = [
  "short",
  "standard",
  "detailed",
] as const;
export type PractitionerLearningProfilePreferredDocumentLength = (typeof PRACTITIONER_LEARNING_PROFILE_PREFERRED_DOCUMENT_LENGTH_VALUES)[number];

export const PRACTITIONER_LEARNING_PROFILE_PREFERRED_STYLE_VALUES = [
  "sentences",
  "semi_telegraphic",
] as const;
export type PractitionerLearningProfilePreferredStyle = (typeof PRACTITIONER_LEARNING_PROFILE_PREFERRED_STYLE_VALUES)[number];

export interface TranscriptSegment {
  segment_id: string;
  start_ms: number;
  end_ms: number;
  speaker_role: TranscriptSegmentSpeakerRole;
  text: string;
  confidence: number;
  is_final: boolean;
}

export interface ClinicalFact {
  fact_id: string;
  category: ClinicalFactCategory;
  concept: string;
  value: unknown;
  teeth: string[];
  surfaces: ClinicalFactSurfaces[];
  assertion: ClinicalFactAssertion;
  temporality: ClinicalFactTemporality;
  clinical_status: ClinicalFactClinicalStatus;
  speaker_role: ClinicalFactSpeakerRole;
  certainty: ClinicalFactCertainty;
  source_type: ClinicalFactSourceType;
  evidence_segment_ids: string[];
  confidence: number;
  manually_validated: boolean;
}

export interface TreatmentPlanItem {
  item_id: string;
  teeth: string[];
  problem: string | null;
  action: string;
  status: TreatmentPlanItemStatus;
  priority: TreatmentPlanItemPriority;
  sequence: number | null;
  alternatives: string[];
  prerequisites: string[];
  uncertainties: string[];
  evidence_fact_ids: string[];
}

export interface TreatmentPlan {
  plan_id: string;
  status: TreatmentPlanStatus;
  goals: string[];
  notes: string[];
  items: TreatmentPlanItem[];
}

export interface Procedure {
  procedure_id: string;
  procedure_type: ProcedureProcedureType;
  status: ProcedureStatus;
  teeth: string[];
  structured_data: Record<string, unknown>;
  evidence_fact_ids: string[];
}

export interface EncounterWarning {
  code: string;
  severity: EncounterWarningSeverity;
  message: string;
}

export interface ClinicalEncounter {
  encounter_id: string;
  patient_id: string;
  practitioner_id: string;
  started_at: string;
  ended_at: string | null;
  status: ClinicalEncounterStatus;
  object_version: number;
  facts: ClinicalFact[];
  treatment_plan: TreatmentPlan | null;
  procedures: Procedure[];
  warnings: EncounterWarning[];
}

export interface Document {
  document_id: string;
  document_type: DocumentDocumentType;
  status: DocumentStatus;
  encounter_object_version: number;
  content: string;
  supported_fact_ids: string[];
}

export interface LearningEvent {
  learning_event_id: string;
  organization_id: string;
  user_id: string;
  encounter_id: string;
  event_type: LearningEventEventType;
  scope: LearningEventScope;
  source_version: string;
  before: unknown;
  after: unknown;
  reason?: string | null;
  confidence_before?: number | null;
  validated_by_practitioner: boolean;
  created_at: string;
  eligible_for_global_learning: boolean;
  learning_status: LearningEventLearningStatus;
}

export interface SpeechAlias {
  heard: string;
  canonical: string;
}

export interface PractitionerLearningProfile {
  user_id: string;
  preferred_document_length: PractitionerLearningProfilePreferredDocumentLength;
  preferred_style: PractitionerLearningProfilePreferredStyle;
  preferred_terms: Record<string, string>;
  frequent_materials: string[];
  speech_aliases: SpeechAlias[];
  document_preferences: Record<string, unknown>;
  last_updated_at: string;
}

export interface EvaluationRun {
  evaluation_run_id: string;
  component: string;
  candidate_version: string;
  dataset_version: string;
  metrics: Record<string, number>;
  critical_regressions: string[];
  created_at: string;
  release_gate_passed: boolean;
}
