"""Un vrai compte : mot de passe du praticien, et garde contre les essais répétés.

Jusqu'ici, relier un iPhone demandait de recopier à la main un jeton de quarante-huit
caractères. Franck, le 24/10/2026 : « j'en ai marre de mettre des jetons, c'est chiant ».
Il a raison — c'était un défaut de conception. Le jeton reste ce qui circule à chaque
appel ; ce qui change, c'est qu'on l'obtient désormais en se connectant, comme partout
ailleurs. (Étape 1 de la feuille de route de commercialisation.)

L'empreinte est un scrypt, comme celle des jetons : un vol de base ne rend aucun mot de
passe utilisable. `essais_rates` et `bloque_jusqua` rendent la devinette coûteuse.

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-24 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("password_salt", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("failed_logins", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_logins")
    op.drop_column("users", "password_salt")
    op.drop_column("users", "password_hash")
