"""Modèles d'échange de l'API (hors objets cliniques, qui viennent des contrats générés)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from oris_api.contracts import ClinicalEncounter, TranscriptSegment
from oris_api.contracts.generated import (
    ClinicalEncounterStatus,
    DocumentDocumentType,
    DocumentStatus,
    LearningEventEventType,
)
from oris_api.domain.corrections import CorrectionOperation

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ApiErrorBody(BaseModel):
    code: str
    subject_id: str | None = None
    details: list[str] = []


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name
    last_name: Name
    birth_date: date | None = None
    external_id: str | None = None


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name | None = None
    last_name: Name | None = None
    birth_date: date | None = None
    external_id: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    external_id: str | None
    created_at: datetime


class EncounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: UUID
    synthetic_case_id: str | None = None


class ProcessingError(BaseModel):
    rule: str
    subject_id: str


class DocumentSummary(BaseModel):
    id: UUID
    document_type: DocumentDocumentType
    status: DocumentStatus


class EncounterOut(BaseModel):
    id: UUID
    patient: PatientOut
    status: ClinicalEncounterStatus
    object_version: int
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    synthetic_case_id: str | None
    processing_errors: list[ProcessingError]
    critical_warning_count: int
    documents: list[DocumentSummary]


class ClaimOut(BaseModel):
    section: str
    text: str
    fact_ids: list[str]
    warning_codes: list[str]


class ValidationIssueOut(BaseModel):
    code: str
    severity: str
    fact_id: str | None
    claim_index: int | None


class DocumentOut(BaseModel):
    id: UUID
    encounter_id: UUID
    document_type: DocumentDocumentType
    status: DocumentStatus
    version: int
    generated_from_object_version: int
    is_current: bool
    content: str
    claims: list[ClaimOut]
    supported_fact_ids: list[str]
    validation_issues: list[ValidationIssueOut]
    generator: str
    created_at: datetime
    validated_at: datetime | None


class DocumentValidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acknowledged_warning_codes: list[str] = []


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_object_version: Annotated[int, Field(ge=1)]
    operations: Annotated[list[CorrectionOperation], Field(min_length=1, max_length=20)]
    regenerate: bool = True


class ObjectVersionOut(BaseModel):
    version: int
    change_kind: str
    created_at: datetime
    created_by: UUID | None


class TranscriptOut(BaseModel):
    encounter_id: UUID
    segments: list[TranscriptSegment]


class ClinicalObjectOut(BaseModel):
    clinical_object: ClinicalEncounter
    versions: list[ObjectVersionOut]


class LearningEventOut(BaseModel):
    learning_event_id: UUID
    event_type: LearningEventEventType
    scope: str
    source_version: str
    before: Any
    after: Any
    confidence_before: float | None
    validated_by_practitioner: bool
    eligible_for_global_learning: bool
    learning_status: str
    created_at: datetime


class SyntheticCaseOut(BaseModel):
    case_id: str
    domain: str
    tags: list[str]
    patient_first_name: str
    patient_last_name: str
    segment_count: int
