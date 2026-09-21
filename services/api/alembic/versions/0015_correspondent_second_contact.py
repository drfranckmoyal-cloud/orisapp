"""Une seconde adresse et un second numéro pour un correspondant.

Un confrère a souvent deux numéros — le cabinet et le portable — et parfois deux
adresses, celle du secrétariat et la sienne. Les écraser l'une par l'autre obligeait à
choisir laquelle on perd.

Deux champs de plus, vides par défaut : le cas courant reste un seul contact, et le
formulaire ne montre le second que si on le demande.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-21 10:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "correspondents",
        sa.Column("secondary_email", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column(
        "correspondents",
        sa.Column("secondary_phone", sa.String(length=40), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("correspondents", "secondary_phone")
    op.drop_column("correspondents", "secondary_email")
