"""Modèles d'échange de l'API (hors objets cliniques, qui viennent des contrats générés)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal
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
from oris_api.services.audio import GapReason

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ApiErrorBody(BaseModel):
    code: str
    subject_id: str | None = None
    details: list[str] = []


# Note administrative (§9) : « courte » est une contrainte du cadrage, pas un détail.
# Un champ long inviterait à y écrire du clinique, qu'Oris ne lira jamais.
AdminNote = Annotated[str, StringConstraints(max_length=500)]


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name
    last_name: Name
    birth_date: date | None = None
    external_id: str | None = None
    email: Annotated[str, StringConstraints(max_length=200)] = ""
    note: AdminNote = ""


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name | None = None
    last_name: Name | None = None
    birth_date: date | None = None
    external_id: str | None = None
    email: Annotated[str, StringConstraints(max_length=200)] | None = None
    note: AdminNote | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    external_id: str | None
    email: str
    note: str
    created_at: datetime


class EncounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: UUID
    synthetic_case_id: str | None = None
    # Mode ombre : Oris travaille en parallèle, ses sorties ne sont pas utilisables.
    shadow: bool = False


class ProcessingError(BaseModel):
    rule: str
    subject_id: str


class DocumentSummary(BaseModel):
    id: UUID
    document_type: DocumentDocumentType
    status: DocumentStatus


class PractitionerOut(BaseModel):
    """Qui a mené la consultation. Un cabinet à plusieurs praticiens doit le voir."""

    id: UUID
    name: str
    title: str


class EncounterOut(BaseModel):
    id: UUID
    patient: PatientOut
    practitioner: PractitionerOut
    status: ClinicalEncounterStatus
    object_version: int
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    synthetic_case_id: str | None
    mode: str
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


class SpokenCorrectionRequest(BaseModel):
    """Correction dictée ou écrite. Par défaut : aperçu, sans rien modifier."""

    model_config = ConfigDict(extra="forbid")
    command: Annotated[str, Field(min_length=1, max_length=500)]
    expected_object_version: Annotated[int, Field(ge=1)] | None = None
    apply: bool = False


class SpokenCorrectionOut(BaseModel):
    """Ce qu'Oris a compris, et ce qu'il a fait — ou pas."""

    kind: Literal["clinical", "editorial", "unclear"]
    summary: str
    impact: Literal["normal", "high"]
    reason: str
    candidates: list[str]
    operations: list[dict[str, Any]]
    applied: bool
    object_version: int


class DocumentTextEdit(BaseModel):
    """Texte réécrit par le praticien (§48)."""

    model_config = ConfigDict(extra="forbid")
    content: Annotated[str, Field(min_length=1, max_length=20_000)]


class ProgressOut(BaseModel):
    """Avancement réel du traitement : chaque nombre est lu en base (S06)."""

    status: ClinicalEncounterStatus
    transcript_segments: int
    facts: int
    documents: int
    termine: bool


class AttachmentOut(BaseModel):
    """Une pièce jointe. Oris ne la lit pas : elle accompagne, elle ne nourrit pas."""

    id: UUID
    filename: str
    media_type: str
    kind: str
    byte_size: int
    label: str
    encounter_id: UUID | None
    created_at: datetime


class DictationOut(BaseModel):
    """Texte dicté, rendu au praticien. Le son n'est jamais conservé."""

    text: str


class LiveSegmentOut(BaseModel):
    """Une parole entendue en direct. Provisoire tant que `is_final` est faux."""

    segment_id: str
    start_ms: int
    end_ms: int
    speaker_role: str
    text: str
    is_final: bool


class LiveTranscriptOut(BaseModel):
    """Ce qu'Oris entend pendant la consultation (§11, §14.1).

    `state` : `disabled` (écoute en direct éteinte), `idle` (pas encore commencée),
    `running`, `stopped`, `failed`. Cette transcription ne sert jamais au dossier.
    """

    state: str
    error_code: str | None = None
    segments: list[LiveSegmentOut]
    total: int
    reconnections: int


class MarkCreate(BaseModel):
    """Point marqué pendant l'écoute : un instant, rien d'autre (spec §11)."""

    timestamp_ms: Annotated[int, Field(ge=0)]


class MarkOut(BaseModel):
    timestamp_ms: int
    created_at: datetime


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


class EncounterStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_informed: bool = False


class EncounterFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    final_sequence: Annotated[int, Field(ge=-1)] | None = None
    client_recorded_ms: Annotated[int, Field(ge=0)] | None = None
    accept_gaps: bool = False


class ChunkReceiptOut(BaseModel):
    sequence: int
    status: Literal["stored", "duplicate"]


class AudioGapReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: GapReason
    duration_ms: Annotated[int, Field(ge=0)] | None = None


class AudioGapOut(BaseModel):
    duration_ms: int | None


class AudioSessionOut(BaseModel):
    status: str
    audio_format: str
    received_count: int
    last_sequence: int | None
    next_sequence: int
    next_timestamp_ms: int
    missing_sequences: list[int]
    received_duration_ms: int
    gaps: list[AudioGapOut]
    reported_gap_reasons: list[str]
    purge_status: str
    finalized_at: datetime | None
    purged_at: datetime | None
    last_received_at: datetime | None


class ClientConfigOut(BaseModel):
    environment: str
    audio_format: str
    sample_rate: int
    chunk_duration_ms: int
    max_chunk_bytes: int
    max_session_minutes: int
    warn_session_minutes: int
    patient_information_mode: Literal["none", "confirm"]
    test_audio_source_enabled: bool
    # Formats de pièces jointes acceptés, et connecteurs disponibles.
    attachment_formats: list[str]
    attachment_max_bytes: int
    smilecloud_connected: bool
