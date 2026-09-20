"""Note administrative courte sur la fiche patient (spec §9).

« Note administrative », et le mot compte : elle sert au praticien pour un rappel
pratique (« préfère le matin », « à rappeler au cabinet »). Elle n'est jamais lue par
Oris, n'entre dans aucun compte rendu et ne produit aucun fait clinique.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-20 23:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("patients", "note")
