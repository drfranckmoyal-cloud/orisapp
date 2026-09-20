"""Modèle de données (spec §56–57).

Deux stores logiquement séparés (ACCEPTANCE_CRITERIA §Learning) :
- schéma `public` : dossier patient et objet clinique ;
- schéma `learning` : LearningEvents, sans clé étrangère vers le dossier patient.

Les faits, plans, actes et documents gardent la clé de contrat (`fact_id`,
`item_id`…) utilisée dans l'objet clinique JSON, unique par consultation, en
plus d'une clé primaire UUID interne. Les liens de preuve (fait -> segment,
élément de plan / acte -> fait) sont des tables à clés étrangères.

L'objet clinique complet de chaque version est conservé dans
`encounter_object_versions` (source de vérité et historique) ; les tables de
faits, plan et actes en sont la projection pour la version courante.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from oris_api.contracts.generated import (
    ClinicalEncounterStatus,
    ClinicalFactAssertion,
    ClinicalFactCategory,
    ClinicalFactCertainty,
    ClinicalFactClinicalStatus,
    ClinicalFactSourceType,
    ClinicalFactSpeakerRole,
    ClinicalFactTemporality,
    DocumentDocumentType,
    DocumentStatus,
    LearningEventEventType,
    LearningEventLearningStatus,
    LearningEventScope,
    ProcedureProcedureType,
    ProcedureStatus,
    TranscriptSegmentSpeakerRole,
    TreatmentPlanItemPriority,
    TreatmentPlanItemStatus,
    TreatmentPlanStatus,
)
from oris_api.db.base import Base, contract_enum, created_at, updated_at, uuid_pk

UserRole = Literal["practitioner", "assistant", "admin"]  # spec §62
ObjectChangeKind = Literal["extraction", "correction", "status_change"]
AudioSessionStatus = Literal["open", "finalized"]
AudioPurgeStatus = Literal["retained", "purged"]

LEARNING_SCHEMA = "learning"


def jsonb(default: Any) -> Mapped[Any]:
    return mapped_column(JSONB, nullable=False, default=default)


# --- Organisation et utilisateurs ----------------------------------------------


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    # En-tête des documents : adresse, téléphone, mention légale… (spec §78).
    identity: Mapped[dict[str, Any]] = jsonb(dict)
    created_at: Mapped[datetime] = created_at()


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(contract_enum(UserRole, "user_role"))
    preferences: Mapped[dict[str, Any]] = jsonb(dict)
    created_at: Mapped[datetime] = created_at()


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(contract_enum(UserRole, "member_role"))
    created_at: Mapped[datetime] = created_at()


# --- Patient et consultation -----------------------------------------------------


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(200))
    last_name: Mapped[str] = mapped_column(String(200))
    birth_date: Mapped[date | None] = mapped_column(Date)
    external_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class Encounter(Base):
    """Consultation. `object_version` versionne l'objet clinique (spec §57)."""

    __tablename__ = "encounters"
    __table_args__ = (CheckConstraint("object_version >= 1", name="object_version_positive"),)

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    practitioner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(
        contract_enum(ClinicalEncounterStatus, "encounter_status"), default="draft"
    )
    mode: Mapped[str] = mapped_column(String(32), default="consultation")
    object_version: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class EncounterMarkRow(Base):
    """Repère temporel posé par le praticien pendant l'écoute (spec §11).

    Ce n'est pas une donnée clinique : rien de ce qui est marqué n'entre dans
    l'objet clinique. C'est un signet pour retrouver un moment à la relecture.
    """

    __tablename__ = "encounter_marks"
    __table_args__ = (
        CheckConstraint("timestamp_ms >= 0", name="mark_timestamp_positive"),
        UniqueConstraint("encounter_id", "timestamp_ms", name="uq_encounter_marks_moment"),
    )

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at()


class TranscriptSegmentRow(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("encounter_id", "segment_id", name="uq_transcript_segments_key"),
        CheckConstraint("end_ms >= start_ms", name="time_order"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    segment_id: Mapped[str] = mapped_column(String(64))
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    speaker_role: Mapped[str] = mapped_column(
        contract_enum(TranscriptSegmentSpeakerRole, "segment_speaker_role")
    )
    text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    is_final: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()


# --- Faits cliniques ---------------------------------------------------------------


class ClinicalFactRow(Base):
    __tablename__ = "clinical_facts"
    __table_args__ = (
        UniqueConstraint("encounter_id", "fact_id", name="uq_clinical_facts_key"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    fact_id: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(contract_enum(ClinicalFactCategory, "fact_category"))
    concept: Mapped[str] = mapped_column(String(200))
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    teeth: Mapped[list[str]] = jsonb(list)
    surfaces: Mapped[list[str]] = jsonb(list)
    assertion: Mapped[str] = mapped_column(contract_enum(ClinicalFactAssertion, "fact_assertion"))
    temporality: Mapped[str] = mapped_column(
        contract_enum(ClinicalFactTemporality, "fact_temporality")
    )
    clinical_status: Mapped[str] = mapped_column(
        contract_enum(ClinicalFactClinicalStatus, "fact_clinical_status")
    )
    speaker_role: Mapped[str] = mapped_column(
        contract_enum(ClinicalFactSpeakerRole, "fact_speaker_role")
    )
    certainty: Mapped[str] = mapped_column(contract_enum(ClinicalFactCertainty, "fact_certainty"))
    source_type: Mapped[str] = mapped_column(
        contract_enum(ClinicalFactSourceType, "fact_source_type")
    )
    confidence: Mapped[float] = mapped_column(Float)
    manually_validated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class FactEvidenceLink(Base):
    __tablename__ = "fact_evidence_links"

    fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinical_facts.id", ondelete="CASCADE"), primary_key=True
    )
    transcript_segment_id: Mapped[UUID] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE"), primary_key=True
    )


# --- Plan de traitement et actes -----------------------------------------------------


class TreatmentPlanRow(Base):
    __tablename__ = "treatment_plans"

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), unique=True
    )
    plan_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(contract_enum(TreatmentPlanStatus, "plan_status"))
    goals: Mapped[list[str]] = jsonb(list)
    notes: Mapped[list[str]] = jsonb(list)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class TreatmentPlanItemRow(Base):
    __tablename__ = "treatment_plan_items"
    __table_args__ = (
        UniqueConstraint("plan_id", "item_id", name="uq_treatment_plan_items_key"),
        CheckConstraint("sequence IS NULL OR sequence >= 1", name="sequence_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("treatment_plans.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[str] = mapped_column(String(64))
    teeth: Mapped[list[str]] = jsonb(list)
    problem: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(contract_enum(TreatmentPlanItemStatus, "plan_item_status"))
    priority: Mapped[str] = mapped_column(
        contract_enum(TreatmentPlanItemPriority, "plan_item_priority")
    )
    # Séquence uniquement si explicitement énoncée (spec §33.3) : NULL sinon.
    sequence: Mapped[int | None] = mapped_column(Integer)
    alternatives: Mapped[list[str]] = jsonb(list)
    prerequisites: Mapped[list[str]] = jsonb(list)
    uncertainties: Mapped[list[str]] = jsonb(list)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class TreatmentPlanItemEvidence(Base):
    __tablename__ = "treatment_plan_item_evidence"

    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("treatment_plan_items.id", ondelete="CASCADE"), primary_key=True
    )
    fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinical_facts.id", ondelete="CASCADE"), primary_key=True
    )


class ProcedureRow(Base):
    __tablename__ = "procedures"
    __table_args__ = (UniqueConstraint("encounter_id", "procedure_id", name="uq_procedures_key"),)

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    procedure_id: Mapped[str] = mapped_column(String(64))
    procedure_type: Mapped[str] = mapped_column(
        contract_enum(ProcedureProcedureType, "procedure_type")
    )
    status: Mapped[str] = mapped_column(contract_enum(ProcedureStatus, "procedure_status"))
    teeth: Mapped[list[str]] = jsonb(list)
    # Emplacements renseignés uniquement par des faits énoncés, jamais par défaut.
    structured_data: Mapped[dict[str, Any]] = jsonb(dict)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class ProcedureEvidence(Base):
    __tablename__ = "procedure_evidence"

    procedure_id: Mapped[UUID] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), primary_key=True
    )
    fact_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinical_facts.id", ondelete="CASCADE"), primary_key=True
    )


# --- Documents (projections de l'objet clinique, D008) -------------------------------


class DocumentRow(Base):
    """Un document par type et par consultation ; son contenu vit dans ses versions."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("encounter_id", "document_type", name="uq_documents_encounter_type"),
    )

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    document_type: Mapped[str] = mapped_column(contract_enum(DocumentDocumentType, "document_type"))
    status: Mapped[str] = mapped_column(contract_enum(DocumentStatus, "document_status"))
    current_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_versions.id", use_alter=True, ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class DocumentVersion(Base):
    """Version immuable d'un document, rattachée à la version d'objet qui l'a produite.

    `claims` : phrases et faits/alertes qui les appuient (provenance, §30).
    `supported_fact_ids` : clés de faits de l'objet `generated_from_object_version`.
    """

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_versions_version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("generated_from_object_version >= 1", name="object_version_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    claims: Mapped[list[dict[str, Any]]] = jsonb(list)
    supported_fact_ids: Mapped[list[str]] = jsonb(list)
    validation_issues: Mapped[list[dict[str, Any]]] = jsonb(list)
    generated_from_object_version: Mapped[int] = mapped_column(Integer)
    # NULL si produit par un fournisseur ; l'identité du générateur est dans generator.
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    generator: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = created_at()
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    acknowledged_warning_codes: Mapped[list[str]] = jsonb(list)


class EncounterObjectVersion(Base):
    """Objet clinique complet à une version donnée : source de vérité, append-only (§57)."""

    __tablename__ = "encounter_object_versions"
    __table_args__ = (
        UniqueConstraint("encounter_id", "version", name="uq_encounter_object_versions_version"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    clinical_object: Mapped[dict[str, Any]] = jsonb(dict)
    change_kind: Mapped[str] = mapped_column(contract_enum(ObjectChangeKind, "object_change_kind"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at()


# --- Audio (métadonnées seulement ; le son vit dans un stockage transitoire) ----------


class AudioSession(Base):
    __tablename__ = "audio_sessions"

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(contract_enum(AudioSessionStatus, "audio_session_status"))
    audio_format: Mapped[str] = mapped_column(String(100))
    final_sequence: Mapped[int | None] = mapped_column(Integer)
    client_recorded_ms: Mapped[int | None] = mapped_column(Integer)
    # Interruptions signalées par le client : [{"reason", "duration_ms"}].
    reported_gaps: Mapped[list[dict[str, Any]]] = jsonb(list)
    purge_status: Mapped[str] = mapped_column(
        contract_enum(AudioPurgeStatus, "audio_purge_status"), default="retained"
    )
    started_at: Mapped[datetime] = created_at()
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AudioChunkRow(Base):
    __tablename__ = "audio_chunks"
    __table_args__ = (
        UniqueConstraint("audio_session_id", "sequence", name="uq_audio_chunks_sequence"),
        CheckConstraint("sequence >= 0", name="sequence_positive"),
        CheckConstraint("timestamp_ms >= 0 AND duration_ms > 0", name="timing_valid"),
    )

    id: Mapped[UUID] = uuid_pk()
    audio_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("audio_sessions.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    byte_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = created_at()


# --- Audit (identifiants uniquement, jamais de contenu clinique) ------------------------


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = uuid_pk()
    occurred_at: Mapped[datetime] = created_at()
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID] = mapped_column(index=True)
    details: Mapped[dict[str, Any]] = jsonb(dict)


# --- Learning store (schéma séparé, sans clé étrangère vers le dossier patient) ---------


class LearningEventRow(Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        CheckConstraint(
            "confidence_before IS NULL OR (confidence_before >= 0 AND confidence_before <= 1)",
            name="confidence_before_range",
        ),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(index=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    encounter_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(
        contract_enum(LearningEventEventType, "learning_event_type")
    )
    scope: Mapped[str] = mapped_column(contract_enum(LearningEventScope, "learning_scope"))
    source_version: Mapped[str] = mapped_column(String(100))
    before: Mapped[Any] = mapped_column(JSONB, nullable=True)
    after: Mapped[Any] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text)
    confidence_before: Mapped[float | None] = mapped_column(Float)
    validated_by_practitioner: Mapped[bool] = mapped_column(default=False)
    # Une préférence locale ne devient jamais globale automatiquement.
    eligible_for_global_learning: Mapped[bool] = mapped_column(default=False)
    learning_status: Mapped[str] = mapped_column(
        contract_enum(LearningEventLearningStatus, "learning_status"), default="captured"
    )
    created_at: Mapped[datetime] = created_at()


class GlossaryTermRow(Base):
    """Dictionnaire personnel du praticien (spec §54, §120).

    Vit dans le magasin d'apprentissage, jamais dans le dossier patient : un terme
    appris améliore la reconnaissance et la rédaction, il n'ajoute aucun fait clinique.
    """

    __tablename__ = "glossary_terms"
    __table_args__ = (
        UniqueConstraint("user_id", "canonical", name="uq_glossary_terms_user_canonical"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="glossary_confidence_range"),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(index=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    canonical: Mapped[str] = mapped_column(String(200))
    aliases: Mapped[list[str]] = jsonb(list)
    category: Mapped[str] = mapped_column(String(40), default="other")
    # `suggested` : proposé par Oris à partir de corrections répétées, pas encore retenu.
    origin: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="active")
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    scope: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class ApiToken(Base):
    """Jeton d'accès d'un praticien (docs/SECURITY.md).

    Seule l'empreinte est stockée : un vol de base ne rend aucun jeton utilisable.
    Un jeton se révoque ; il ne se modifie pas.
    """

    __tablename__ = "api_tokens"

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    # scrypt(secret, sel) — ni le secret ni un condensé réversible.
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    salt: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = created_at()
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
