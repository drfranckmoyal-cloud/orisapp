"""Rattacher un patient à ses correspondants.

Deux sens très différents se cachent derrière le mot « correspondant » : **qui a adressé
ce patient**, et **à qui on l'adresse**. Le premier dit d'où viennent les patients du
cabinet, le second à qui écrire. Un troisième cas existe — un confrère qui suit le
patient sans l'avoir adressé ni le recevoir de nous.

D'où un rôle porté par le lien, et non par le correspondant : le même confrère adresse
un patient et en reçoit un autre.

Un correspondant n'apparaît qu'une fois par patient : deux lignes pour la même personne,
avec deux rôles, seraient illisibles sur la fiche et sans usage réel.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-21 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_correspondents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "patient_id",
            sa.Uuid(),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "correspondent_id",
            sa.Uuid(),
            sa.ForeignKey("correspondents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role in ('referred_by', 'referred_to', 'also_follows')",
            name="patient_correspondent_role",
        ),
        sa.UniqueConstraint("patient_id", "correspondent_id", name="uq_patient_correspondent_pair"),
    )
    op.create_index(
        "ix_patient_correspondents_patient_id", "patient_correspondents", ["patient_id"]
    )
    op.create_index(
        "ix_patient_correspondents_correspondent_id",
        "patient_correspondents",
        ["correspondent_id"],
    )
    op.create_index(
        "ix_patient_correspondents_organization_id",
        "patient_correspondents",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_patient_correspondents_organization_id", table_name="patient_correspondents")
    op.drop_index("ix_patient_correspondents_correspondent_id", table_name="patient_correspondents")
    op.drop_index("ix_patient_correspondents_patient_id", table_name="patient_correspondents")
    op.drop_table("patient_correspondents")
