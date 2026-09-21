"""Taille de chaque photo dans la « Documentation clinique » : pleine largeur ou moitié.

Le praticien choisit ; Oris ne décide plus seul que la première photo est en grand.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-21 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_figures",
        sa.Column("format", sa.String(length=10), nullable=False, server_default="demi"),
    )
    # Les photos déjà posées gardent la mise en page qu'elles avaient : la première en grand.
    op.execute("UPDATE document_figures SET format = 'large' WHERE position = 0")


def downgrade() -> None:
    op.drop_column("document_figures", "format")
