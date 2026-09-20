"""Infrastructure d'apprentissage exigée dès la fondation (spec §56, §202, §205).

Huit tables. Aucune ne contient de contenu patient : ni transcription, ni fait, ni
document, ni nom. `templates` et `attachments` sont prévues par le cadrage et restent
inactives en V1 — elles existent pour ne pas avoir à migrer plus tard.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-20 22:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())
LEARNING = "learning"


def upgrade() -> None:
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component", sa.String(length=60), nullable=False),
        sa.Column("version", sa.String(length=60), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("component", "version", name="uq_prompt_versions_component_version"),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_prompt_versions_component", "prompt_versions", ["component"], schema=LEARNING
    )

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("model_id", sa.String(length=160), nullable=False),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component", "provider", "model_id", name="uq_model_versions_component_model"
        ),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_model_versions_component", "model_versions", ["component"], schema=LEARNING
    )

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=60), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("nature", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_dataset_versions_name_version"),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_dataset_versions_name", "dataset_versions", ["name"], schema=LEARNING
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component", sa.String(length=60), nullable=False),
        sa.Column("candidate_version", sa.String(length=160), nullable=False),
        sa.Column("dataset_version", sa.String(length=120), nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("critical_regressions", JSONB, nullable=False),
        sa.Column("release_gate_passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_evaluation_runs_component", "evaluation_runs", ["component"], schema=LEARNING
    )

    op.create_table(
        "practitioner_learning_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_practitioner_learning_profiles_user_id",
        "practitioner_learning_profiles",
        ["user_id"],
        unique=True,
        schema=LEARNING,
    )

    op.create_table(
        "model_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("component", sa.String(length=60), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("counters", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema=LEARNING,
    )
    op.create_index(
        "ix_learning_model_runs_encounter_id", "model_runs", ["encounter_id"], schema=LEARNING
    )
    op.create_index(
        "ix_learning_model_runs_component", "model_runs", ["component"], schema=LEARNING
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("schema_json", JSONB, nullable=False),
        sa.Column("prompt_config_json", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_templates_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "type", "name", name="uq_templates_org_type_name"),
    )
    op.create_index("ix_templates_organization_id", "templates", ["organization_id"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_attachments_encounter_id_encounters",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attachments_encounter_id", "attachments", ["encounter_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("templates")
    op.drop_table("model_runs", schema=LEARNING)
    op.drop_table("practitioner_learning_profiles", schema=LEARNING)
    op.drop_table("evaluation_runs", schema=LEARNING)
    op.drop_table("dataset_versions", schema=LEARNING)
    op.drop_table("model_versions", schema=LEARNING)
    op.drop_table("prompt_versions", schema=LEARNING)
