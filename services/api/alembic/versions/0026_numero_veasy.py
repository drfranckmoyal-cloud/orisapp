"""Le numéro du patient dans Veasy, pour y déposer ses documents.

Franck, le 25/11/2026 : « il faut qu'Oris puisse déposer directement le compte rendu dans
le dossier Veasy du patient ». L'extension Chrome retrouve le dossier une première fois
par le nom et la date de naissance ; Oris retient ensuite son numéro.

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-25 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("veasy_id", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "veasy_id")
