"""Schéma initial : dossier clinique (public) et learning store (schéma learning).

Relu après autogénération : création/suppression du schéma `learning`, et clé
étrangère circulaire documents.current_version_id -> document_versions ajoutée
après la création des deux tables.

Revision ID: 0001
Revises:
Create Date: 2026-09-16 23:51:47.371732
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS learning")
    op.create_table(
        "learning_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
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
                name="learning_event_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "scope",
            sa.Enum(
                "user",
                "organization",
                "global_candidate",
                name="learning_scope",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("source_version", sa.String(length=100), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("confidence_before", sa.Float(), nullable=True),
        sa.Column("validated_by_practitioner", sa.Boolean(), nullable=False),
        sa.Column("eligible_for_global_learning", sa.Boolean(), nullable=False),
        sa.Column(
            "learning_status",
            sa.Enum(
                "captured",
                "reviewed",
                "promoted",
                "rejected",
                "purged",
                name="learning_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_before IS NULL OR (confidence_before >= 0 AND confidence_before <= 1)",
            name=op.f("ck_learning_events_confidence_before_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_events")),
        schema="learning",
    )
    op.create_index(
        op.f("ix_learning_learning_events_encounter_id"),
        "learning_events",
        ["encounter_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        op.f("ix_learning_learning_events_organization_id"),
        "learning_events",
        ["organization_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        op.f("ix_learning_learning_events_user_id"),
        "learning_events",
        ["user_id"],
        unique=False,
        schema="learning",
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "practitioner",
                "assistant",
                "admin",
                name="user_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_audit_events_actor_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)
    op.create_table(
        "organization_members",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "practitioner",
                "assistant",
                "admin",
                name="member_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_members_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_organization_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("organization_id", "user_id", name=op.f("pk_organization_members")),
    )
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=200), nullable=False),
        sa.Column("last_name", sa.String(length=200), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_patients_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )
    op.create_index(
        op.f("ix_patients_organization_id"), "patients", ["organization_id"], unique=False
    )
    op.create_table(
        "encounters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("practitioner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
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
                name="encounter_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("object_version", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "object_version >= 1", name=op.f("ck_encounters_object_version_positive")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_encounters_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patients.id"], name=op.f("fk_encounters_patient_id_patients")
        ),
        sa.ForeignKeyConstraint(
            ["practitioner_id"], ["users.id"], name=op.f("fk_encounters_practitioner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_encounters")),
    )
    op.create_index(
        op.f("ix_encounters_organization_id"), "encounters", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_encounters_patient_id"), "encounters", ["patient_id"], unique=False)
    op.create_index(
        op.f("ix_encounters_practitioner_id"), "encounters", ["practitioner_id"], unique=False
    )
    op.create_table(
        "clinical_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("fact_id", sa.String(length=64), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
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
                name="fact_category",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("concept", sa.String(length=200), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("teeth", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("surfaces", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "assertion",
            sa.Enum(
                "present",
                "absent",
                "uncertain",
                name="fact_assertion",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "temporality",
            sa.Enum(
                "past",
                "current",
                "future",
                name="fact_temporality",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "clinical_status",
            sa.Enum(
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
                name="fact_clinical_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "speaker_role",
            sa.Enum(
                "practitioner",
                "patient",
                "assistant",
                "companion",
                "unknown",
                "manual",
                name="fact_speaker_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "certainty",
            sa.Enum(
                "certain",
                "probable",
                "possible",
                "unknown",
                name="fact_certainty",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum(
                "audio",
                "manual",
                "prior_record",
                "system_test",
                name="fact_source_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("manually_validated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_clinical_facts_confidence_range")
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_clinical_facts_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinical_facts")),
        sa.UniqueConstraint("encounter_id", "fact_id", name="uq_clinical_facts_key"),
    )
    op.create_index(
        op.f("ix_clinical_facts_encounter_id"), "clinical_facts", ["encounter_id"], unique=False
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "consultation_note",
                "treatment_plan_text",
                "operative_note",
                "patient_summary",
                "referral_letter",
                name="document_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft_ai",
                "needs_review",
                "validated",
                "exported",
                "superseded",
                "outdated",
                name="document_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_documents_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_encounter_id"), "documents", ["encounter_id"], unique=False)
    op.create_table(
        "procedures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("procedure_id", sa.String(length=64), nullable=False),
        sa.Column(
            "procedure_type",
            sa.Enum(
                "composite",
                "direct_aesthetic",
                "veneer_preparation",
                "veneer_bonding",
                "wear_additive",
                "extraction",
                "minor_surgery_generic",
                name="procedure_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "planned",
                "performed",
                "cancelled",
                name="procedure_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("teeth", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("structured_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_procedures_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_procedures")),
        sa.UniqueConstraint("encounter_id", "procedure_id", name="uq_procedures_key"),
    )
    op.create_index(
        op.f("ix_procedures_encounter_id"), "procedures", ["encounter_id"], unique=False
    )
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.String(length=64), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column(
            "speaker_role",
            sa.Enum(
                "practitioner",
                "patient",
                "assistant",
                "companion",
                "unknown",
                name="segment_speaker_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_transcript_segments_confidence_range"),
        ),
        sa.CheckConstraint("end_ms >= start_ms", name=op.f("ck_transcript_segments_time_order")),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_transcript_segments_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transcript_segments")),
        sa.UniqueConstraint("encounter_id", "segment_id", name="uq_transcript_segments_key"),
    )
    op.create_index(
        op.f("ix_transcript_segments_encounter_id"),
        "transcript_segments",
        ["encounter_id"],
        unique=False,
    )
    op.create_table(
        "treatment_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "review",
                "validated",
                "superseded",
                name="plan_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("goals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_treatment_plans_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treatment_plans")),
        sa.UniqueConstraint("encounter_id", name=op.f("uq_treatment_plans_encounter_id")),
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generated_from_object_version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("generator", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generated_from_object_version >= 1",
            name=op.f("ck_document_versions_object_version_positive"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_document_versions_version_positive")),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_document_versions_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_versions_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_versions")),
        sa.UniqueConstraint("document_id", "version", name="uq_document_versions_version"),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"), "document_versions", ["document_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_documents_current_version_id_document_versions"),
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "fact_evidence_links",
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_segment_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["clinical_facts.id"],
            name=op.f("fk_fact_evidence_links_fact_id_clinical_facts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transcript_segment_id"],
            ["transcript_segments.id"],
            name=op.f("fk_fact_evidence_links_transcript_segment_id_transcript_segments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "fact_id", "transcript_segment_id", name=op.f("pk_fact_evidence_links")
        ),
    )
    op.create_table(
        "procedure_evidence",
        sa.Column("procedure_id", sa.Uuid(), nullable=False),
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["clinical_facts.id"],
            name=op.f("fk_procedure_evidence_fact_id_clinical_facts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["procedure_id"],
            ["procedures.id"],
            name=op.f("fk_procedure_evidence_procedure_id_procedures"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("procedure_id", "fact_id", name=op.f("pk_procedure_evidence")),
    )
    op.create_table(
        "treatment_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("teeth", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "discussed",
                "proposed",
                "accepted",
                "refused",
                "deferred",
                "planned",
                "completed",
                name="plan_item_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "urgent",
                "high",
                "routine",
                "low",
                "unspecified",
                name="plan_item_priority",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("alternatives", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prerequisites", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("uncertainties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence IS NULL OR sequence >= 1",
            name=op.f("ck_treatment_plan_items_sequence_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["treatment_plans.id"],
            name=op.f("fk_treatment_plan_items_plan_id_treatment_plans"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_treatment_plan_items")),
        sa.UniqueConstraint("plan_id", "item_id", name="uq_treatment_plan_items_key"),
    )
    op.create_index(
        op.f("ix_treatment_plan_items_plan_id"), "treatment_plan_items", ["plan_id"], unique=False
    )
    op.create_table(
        "document_version_facts",
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name=op.f("fk_document_version_facts_document_version_id_document_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["clinical_facts.id"],
            name=op.f("fk_document_version_facts_fact_id_clinical_facts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "document_version_id", "fact_id", name=op.f("pk_document_version_facts")
        ),
    )
    op.create_table(
        "treatment_plan_item_evidence",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_id"],
            ["clinical_facts.id"],
            name=op.f("fk_treatment_plan_item_evidence_fact_id_clinical_facts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["treatment_plan_items.id"],
            name=op.f("fk_treatment_plan_item_evidence_item_id_treatment_plan_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("item_id", "fact_id", name=op.f("pk_treatment_plan_item_evidence")),
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_documents_current_version_id_document_versions"), "documents", type_="foreignkey"
    )
    op.drop_table("treatment_plan_item_evidence")
    op.drop_table("document_version_facts")
    op.drop_index(op.f("ix_treatment_plan_items_plan_id"), table_name="treatment_plan_items")
    op.drop_table("treatment_plan_items")
    op.drop_table("procedure_evidence")
    op.drop_table("fact_evidence_links")
    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_table("treatment_plans")
    op.drop_index(op.f("ix_transcript_segments_encounter_id"), table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_index(op.f("ix_procedures_encounter_id"), table_name="procedures")
    op.drop_table("procedures")
    op.drop_index(op.f("ix_documents_encounter_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_clinical_facts_encounter_id"), table_name="clinical_facts")
    op.drop_table("clinical_facts")
    op.drop_index(op.f("ix_encounters_practitioner_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_patient_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_organization_id"), table_name="encounters")
    op.drop_table("encounters")
    op.drop_index(op.f("ix_patients_organization_id"), table_name="patients")
    op.drop_table("patients")
    op.drop_table("organization_members")
    op.drop_index(op.f("ix_audit_events_entity_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("users")
    op.drop_table("organizations")
    op.drop_index(
        op.f("ix_learning_learning_events_user_id"), table_name="learning_events", schema="learning"
    )
    op.drop_index(
        op.f("ix_learning_learning_events_organization_id"),
        table_name="learning_events",
        schema="learning",
    )
    op.drop_index(
        op.f("ix_learning_learning_events_encounter_id"),
        table_name="learning_events",
        schema="learning",
    )
    op.drop_table("learning_events", schema="learning")
    op.execute("DROP SCHEMA IF EXISTS learning")
