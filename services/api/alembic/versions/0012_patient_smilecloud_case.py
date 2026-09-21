"""Dossier SmileCloud du patient.

Le lien entre un patient d'Oris et son dossier dans SmileCloud, posé une fois par le
praticien puis retenu : sans lui, il faudrait redemander à chaque récupération de
photos quel dossier est le bon.

Il lui faut son propre champ. `external_id` existe déjà mais porte le numéro de dossier
du cabinet, saisi à la main et affiché dans la liste des patients : s'en servir aussi
pour SmileCloud ferait perdre l'un des deux.

Nullable, et il le reste : un patient sans dossier SmileCloud est le cas normal.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-21 09:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("smilecloud_case_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patients", "smilecloud_case_id")
