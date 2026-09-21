"""Adresse d'envoi des courriels, par praticien.

Les documents partent depuis la boîte du praticien qui les signe. L'adresse est un
réglage du profil ; le mot de passe d'envoi, lui, n'entre jamais en base (fichier .env).

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-21 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("sending_email", sa.String(length=320), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("users", "sending_email")
