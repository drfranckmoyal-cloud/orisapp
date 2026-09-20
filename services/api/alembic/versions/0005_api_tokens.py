"""Jetons d'accès des praticiens (M10).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-20 09:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_api_tokens_user_id"), "api_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_tokens_user_id"), table_name="api_tokens")
    op.drop_table("api_tokens")
