"""Dictionnaire personnel du praticien (M9).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-20 08:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "glossary_terms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("canonical", sa.String(length=200), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="glossary_confidence_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "canonical", name="uq_glossary_terms_user_canonical"),
        schema="learning",
    )
    op.create_index(
        op.f("ix_learning_glossary_terms_organization_id"),
        "glossary_terms",
        ["organization_id"],
        unique=False,
        schema="learning",
    )
    op.create_index(
        op.f("ix_learning_glossary_terms_user_id"),
        "glossary_terms",
        ["user_id"],
        unique=False,
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_learning_glossary_terms_user_id"), table_name="glossary_terms", schema="learning"
    )
    op.drop_index(
        op.f("ix_learning_glossary_terms_organization_id"),
        table_name="glossary_terms",
        schema="learning",
    )
    op.drop_table("glossary_terms", schema="learning")
