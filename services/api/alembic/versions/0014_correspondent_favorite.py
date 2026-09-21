"""Correspondant mis en avant.

Un cabinet adresse souvent aux trois ou quatre mêmes confrères, noyés dans un carnet
qui grossit. Les marquer les fait remonter en tête de liste.

À quoi cela servira d'autre n'est pas tranché — proposer d'abord ceux-là au moment
d'adresser un patient, par exemple. Le champ est posé maintenant parce qu'il ne coûte
rien ; ce qu'on en fera viendra après.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-21 10:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "correspondents",
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("correspondents", "favorite")
