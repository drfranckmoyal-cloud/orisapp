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
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
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
    # Dossier du patient dans SmileCloud, posé une fois puis retenu. **Distinct
    # d'`external_id`**, qui porte le numéro de dossier du cabinet : confondre les deux
    # ferait perdre l'un des deux. Donnée personnelle indirecte : jamais journalisée.
    smilecloud_case_id: Mapped[str | None] = mapped_column(String(64))
    # Adresse pour lui envoyer son résumé ou un courrier. Donnée personnelle :
    # jamais journalisée, jamais reprise dans un compte rendu.
    email: Mapped[str] = mapped_column(String(200), default="", server_default="")
    # Note **administrative** du praticien (§9) : un rappel pratique, jamais une
    # donnée clinique. Oris ne la lit pas et ne la reprend dans aucun document.
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
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


# --- Infrastructure d'apprentissage (spec §56, §202, §205) -----------------------------
#
# Le cadrage interdit explicitement de construire une V1 non apprenante puis d'ajouter
# ces mécanismes après coup. Ces tables existent donc dès maintenant, même quand
# l'interface ne les expose pas encore. Aucune ne contient de contenu patient.


class PromptVersion(Base):
    """Une version de consigne donnée au modèle (spec §202).

    Le texte vit dans le code ; ce qui est enregistré ici, c'est son identité et son
    empreinte, pour qu'un résultat puisse toujours être rattaché à la consigne exacte
    qui l'a produit.
    """

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("component", "version", name="uq_prompt_versions_component_version"),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[UUID] = uuid_pk()
    component: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[str] = mapped_column(String(60))
    # sha256 du texte de la consigne : une retouche silencieuse se voit.
    content_hash: Mapped[str] = mapped_column(String(64))
    parameters: Mapped[dict[str, Any]] = jsonb(dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at()


class ModelVersion(Base):
    """Un modèle de fournisseur, tel qu'il a réellement servi (spec §202)."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "component", "provider", "model_id", name="uq_model_versions_component_model"
        ),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[UUID] = uuid_pk()
    component: Mapped[str] = mapped_column(String(60), index=True)
    provider: Mapped[str] = mapped_column(String(60))
    model_id: Mapped[str] = mapped_column(String(160))
    parameters: Mapped[dict[str, Any]] = jsonb(dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at()


class DatasetVersion(Base):
    """Un jeu d'évaluation figé : de quoi rejouer une mesure des mois plus tard."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_dataset_versions_name_version"),
        {"schema": LEARNING_SCHEMA},
    )

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(60))
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    # « synthetic » ou « real » : une mesure sur données jouées ne vaut pas une mesure réelle.
    nature: Mapped[str] = mapped_column(String(20), default="synthetic")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created_at()


class EvaluationRun(Base):
    """Le résultat d'une mesure, et sa porte de sortie (schemas/evaluation_run)."""

    __tablename__ = "evaluation_runs"
    __table_args__ = ({"schema": LEARNING_SCHEMA},)

    id: Mapped[UUID] = uuid_pk()
    component: Mapped[str] = mapped_column(String(60), index=True)
    candidate_version: Mapped[str] = mapped_column(String(160))
    dataset_version: Mapped[str] = mapped_column(String(120))
    metrics: Mapped[dict[str, Any]] = jsonb(dict)
    critical_regressions: Mapped[list[str]] = jsonb(list)
    release_gate_passed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = created_at()


class PractitionerLearningProfile(Base):
    """Ce qu'Oris a retenu d'un praticien, sous la forme du contrat (§202, §205).

    C'est un **miroir** des préférences et du dictionnaire, pas une seconde source :
    il se recalcule, et rien de clinique n'en sort jamais.
    """

    __tablename__ = "practitioner_learning_profiles"
    __table_args__ = ({"schema": LEARNING_SCHEMA},)

    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    profile: Mapped[dict[str, Any]] = jsonb(dict)
    updated_at: Mapped[datetime] = updated_at()


class ModelRun(Base):
    """Un appel à un fournisseur : ce qui a servi, combien de temps, et le résultat.

    Jamais de contenu patient, pas même en métadonnée (spec §56, dernière ligne) :
    ni transcription, ni fait, ni nom, ni texte de document.
    """

    __tablename__ = "model_runs"
    __table_args__ = ({"schema": LEARNING_SCHEMA},)

    id: Mapped[UUID] = uuid_pk()
    encounter_id: Mapped[UUID | None] = mapped_column(index=True)
    component: Mapped[str] = mapped_column(String(60), index=True)
    model_version_id: Mapped[UUID | None] = mapped_column()
    prompt_version_id: Mapped[UUID | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), default="succeeded")
    error_code: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    # Compteurs techniques seulement : nombre de segments, de faits, d'essais.
    counters: Mapped[dict[str, Any]] = jsonb(dict)
    created_at: Mapped[datetime] = created_at()


class Template(Base):
    """Modèle de document propre à un cabinet (spec §56).

    Prévu par le cadrage, inactif en V1 : les modèles de rédaction vivent dans le code
    et sont versionnés avec lui. La table existe pour ne pas avoir à migrer plus tard.
    """

    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "type", "name", name="uq_templates_org_type_name"),
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(160))
    schema_json: Mapped[dict[str, Any]] = jsonb(dict)
    prompt_config_json: Mapped[dict[str, Any]] = jsonb(dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class Attachment(Base):
    """Pièce jointe importée : photo, radio, empreinte, document scanné (§55, §56).

    Elle appartient au **patient** — on l'importe une fois, elle sert à plusieurs
    consultations — et peut être rattachée à l'une d'elles. Le fichier lui-même
    n'est pas dans cette table : seulement où il est rangé, sa taille et son
    empreinte, pour savoir s'il a changé.

    Une pièce jointe n'est **jamais** une source de fait clinique : Oris ne la lit
    pas. Elle accompagne le compte rendu, elle ne le nourrit pas.
    """

    __tablename__ = "attachments"
    __table_args__ = (CheckConstraint("byte_size > 0", name="attachment_size_positive"),)

    id: Mapped[UUID] = uuid_pk()
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("encounters.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(120))
    byte_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(255))
    label: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = created_at()


class Correspondent(Base):
    """Un confrère ou une structure à qui l'on adresse un patient (carnet d'adresses).

    Ce n'est **pas** un utilisateur d'Oris : personne ne s'y connecte. C'est une fiche
    d'adresse, dont la raison d'être est le courrier d'adressage — qui est une vraie
    lettre, et a donc besoin d'une adresse postale autant que d'un nom.
    """

    __tablename__ = "correspondents"
    __table_args__ = (
        CheckConstraint("kind in ('practitioner', 'organisation')", name="correspondent_kind"),
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    #: `practitioner` ou `organisation`. Une structure n'a ni civilité, ni prénom, ni
    #: spécialité — et la lettre ne lui dit pas « Chère Consœur ».
    kind: Mapped[str] = mapped_column(String(20), default="practitioner")
    title: Mapped[str] = mapped_column(String(10), default="", server_default="")
    #: Le nom, ou la raison sociale quand c'est une structure.
    last_name: Mapped[str] = mapped_column(String(200))
    first_name: Mapped[str] = mapped_column(String(200), default="", server_default="")
    #: Le libellé en toutes lettres, pas une clé : renommer une spécialité ne doit pas
    #: réécrire les correspondants. Vide = non renseignée.
    specialty: Mapped[str] = mapped_column(String(80), default="", server_default="")
    practice: Mapped[str] = mapped_column(String(200), default="", server_default="")
    email: Mapped[str] = mapped_column(String(200), default="", server_default="")
    phone: Mapped[str] = mapped_column(String(40), default="", server_default="")
    #: Le second contact : le cabinet et le portable, le secrétariat et lui. Vide dans
    #: le cas courant — le formulaire ne le montre que si on le demande.
    secondary_email: Mapped[str] = mapped_column(String(200), default="", server_default="")
    secondary_phone: Mapped[str] = mapped_column(String(40), default="", server_default="")
    address: Mapped[str] = mapped_column(Text, default="", server_default="")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    #: Mis en avant : remonte en tête de liste. On adresse souvent aux trois ou quatre
    #: mêmes confrères, noyés dans un carnet qui grossit.
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class CorrespondentSpecialty(Base):
    """Une spécialité ajoutée par le cabinet, à côté de celles connues d'avance."""

    __tablename__ = "correspondent_specialties"
    __table_args__ = (
        UniqueConstraint("organization_id", "label", name="uq_correspondent_specialty_label"),
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = created_at()


class PatientCorrespondent(Base):
    """Le lien entre un patient et un correspondant, et ce que ce lien veut dire.

    Le rôle est porté par le **lien**, pas par le correspondant : le même confrère
    adresse un patient et en reçoit un autre.
    """

    __tablename__ = "patient_correspondents"
    __table_args__ = (
        CheckConstraint(
            "role in ('referred_by', 'referred_to', 'also_follows')",
            name="patient_correspondent_role",
        ),
        UniqueConstraint("patient_id", "correspondent_id", name="uq_patient_correspondent_pair"),
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    correspondent_id: Mapped[UUID] = mapped_column(
        ForeignKey("correspondents.id", ondelete="CASCADE"), index=True
    )
    #: `referred_by` (il nous l'a adressé), `referred_to` (nous le lui adressons),
    #: `also_follows` (il le suit aussi, sans que personne n'ait adressé personne).
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = created_at()


class DocumentDelivery(Base):
    """Un document parti chez quelqu'un : à qui, par quel moyen, quand.

    Oris n'envoie rien lui-même : le praticien **note** l'envoi, fait par mail, courrier
    ou remis en main propre. Le nom du destinataire est recopié au moment du geste — un
    correspondant supprimé plus tard ne doit pas effacer la trace de ce qui a été envoyé.
    """

    __tablename__ = "document_deliveries"
    __table_args__ = (
        CheckConstraint(
            "recipient_kind in ('patient', 'correspondent', 'other')",
            name="document_delivery_recipient_kind",
        ),
        CheckConstraint(
            "channel in ('email', 'mail', 'hand', 'secure_messaging', 'other')",
            name="document_delivery_channel",
        ),
    )

    id: Mapped[UUID] = uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    recipient_kind: Mapped[str] = mapped_column(String(20))
    correspondent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("correspondents.id", ondelete="SET NULL"), index=True
    )
    recipient_label: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    sent_at: Mapped[datetime] = created_at()


class DocumentFigure(Base):
    """Une photo placée dans la « Documentation clinique » d'un document.

    La photo reste une pièce jointe du patient : le document la **cite**, avec sa
    légende et sa place. Elle ne nourrit aucun fait — Oris ne lit pas les photos.
    """

    __tablename__ = "document_figures"
    __table_args__ = (
        UniqueConstraint("document_id", "attachment_id", name="uq_document_figure_pair"),
    )

    id: Mapped[UUID] = uuid_pk()
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"), index=True
    )
    caption: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at()
