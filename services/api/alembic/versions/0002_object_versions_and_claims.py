"""Versions de l'objet clinique et phrases justifiées des documents (M1).

Relu après autogénération : valeurs par défaut serveur pour les colonnes JSONB
non nulles ajoutées à une table existante ; document_version_facts supprimée
(les faits cités sont désormais ceux d'une version d'objet, pas des lignes mutables).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17 04:23:58.628519
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "encounter_object_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("clinical_object", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "change_kind",
            sa.Enum(
                "extraction",
                "correction",
                "status_change",
                name="object_change_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version >= 1", name=op.f("ck_encounter_object_versions_version_positive")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_encounter_object_versions_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_encounter_object_versions_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_encounter_object_versions")),
        sa.UniqueConstraint("encounter_id", "version", name="uq_encounter_object_versions_version"),
    )
    op.create_index(
        op.f("ix_encounter_object_versions_encounter_id"),
        "encounter_object_versions",
        ["encounter_id"],
        unique=False,
    )
    op.drop_table("document_version_facts")
    op.add_column(
        "document_versions",
        sa.Column(
            "claims",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "supported_fact_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "validation_issues",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "document_versions", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("document_versions", sa.Column("validated_by", sa.Uuid(), nullable=True))
    op.add_column(
        "document_versions",
        sa.Column(
            "acknowledged_warning_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_document_versions_validated_by_users"),
        "document_versions",
        "users",
        ["validated_by"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_documents_encounter_type", "documents", ["encounter_id", "document_type"]
    )
    for column in (
        "claims",
        "supported_fact_ids",
        "validation_issues",
        "acknowledged_warning_codes",
    ):
        op.alter_column("document_versions", column, server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_documents_encounter_type", "documents", type_="unique")
    op.drop_constraint(
        op.f("fk_document_versions_validated_by_users"), "document_versions", type_="foreignkey"
    )
    op.drop_column("document_versions", "acknowledged_warning_codes")
    op.drop_column("document_versions", "validated_by")
    op.drop_column("document_versions", "validated_at")
    op.drop_column("document_versions", "validation_issues")
    op.drop_column("document_versions", "supported_fact_ids")
    op.drop_column("document_versions", "claims")
    op.create_table(
        "document_version_facts",
        sa.Column("document_version_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("fact_id", sa.UUID(), autoincrement=False, nullable=False),
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
    op.drop_index(
        op.f("ix_encounter_object_versions_encounter_id"), table_name="encounter_object_versions"
    )
    op.drop_table("encounter_object_versions")
