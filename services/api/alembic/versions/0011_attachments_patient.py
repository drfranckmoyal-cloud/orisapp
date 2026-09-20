"""Pièces jointes rattachées au patient (spec §55, §56).

La table existait depuis la fondation, liée à une consultation. Or une photo
clinique appartient d'abord au **patient** : on l'importe une fois, elle sert à
plusieurs consultations. `encounter_id` devient donc facultatif, et `patient_id`
obligatoire.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-21 11:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # La table est vide (aucune route ne l'écrivait) : on peut la refaire proprement.
    op.drop_table("attachments")
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("label", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_attachments_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name="fk_attachments_encounter_id_encounters",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("byte_size > 0", name="attachment_size_positive"),
    )
    op.create_index("ix_attachments_patient_id", "attachments", ["patient_id"])
    op.create_index("ix_attachments_encounter_id", "attachments", ["encounter_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
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
    )
    op.create_index("ix_attachments_encounter_id", "attachments", ["encounter_id"])
