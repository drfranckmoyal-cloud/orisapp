"""Adresse électronique du patient (spec §9, §56).

Elle sert à lui envoyer son résumé ou un courrier. C'est une donnée personnelle :
elle n'a rien à faire dans un journal ni dans un compte rendu.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-21 09:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("email", sa.String(length=200), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("patients", "email")
