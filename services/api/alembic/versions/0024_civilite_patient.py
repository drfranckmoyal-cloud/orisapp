"""La civilité du patient, pour accorder les documents.

Franck, le 27/10/2026, en relisant un compte rendu : « c'est un patient et pas une
patiente ». La fiche ne portait ni Monsieur ni Madame : le rédacteur devinait le genre
d'après le prénom. Un prénom n'est pas un genre.

Donnée de **forme** : elle ne change aucun fait clinique, elle ne sert qu'à accorder.
Vide — « on ne sait pas » est une réponse — Oris écrit sans accorder plutôt que de parier.

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-27 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CIVILITES = ("", "monsieur", "madame")


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "civility",
            sa.String(length=8),
            nullable=False,
            server_default="",
        ),
    )
    op.create_check_constraint(
        "patient_civility",
        "patients",
        "civility IN " + str(CIVILITES),
    )


def downgrade() -> None:
    # Le nom court : la convention de nommage d'Alembic ajoute « ck_patients_ ».
    op.drop_constraint("patient_civility", "patients", type_="check")
    op.drop_column("patients", "civility")
