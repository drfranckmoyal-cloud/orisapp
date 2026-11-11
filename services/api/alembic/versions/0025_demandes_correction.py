"""Les demandes faites à « Corriger avec Claude », gardées en base.

Franck, le 11/11/2026 : « si je sors et que je reviens dans Corriger avec Claude, garder
l'historique, ne pas en remettre une vierge » — et, plus tard le même jour, refus de la
limite « tant que l'app reste ouverte ». La conversation vit donc sur le serveur : elle
survit à l'app fermée, et se retrouve de l'iPhone au site.

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-11 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ETATS = (
    "lecture",
    "proposee",
    "relecture",
    "application",
    "traitee",
    "annulee",
    "incomprise",
    "echec",
)


def upgrade() -> None:
    op.create_table(
        "demandes_correction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column(
            "etat",
            sa.Enum(*ETATS, name="demande_etat", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("reponse", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_demandes_correction_encounter_id"), "demandes_correction", ["encounter_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_demandes_correction_encounter_id"), table_name="demandes_correction")
    op.drop_table("demandes_correction")
