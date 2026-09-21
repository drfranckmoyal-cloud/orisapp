"""Correspondants : les confrères et les structures à qui l'on adresse un patient.

Un correspondant n'est pas un utilisateur d'Oris : c'est un carnet d'adresses. Il sert
à rattacher un patient (qui l'a adressé, à qui on l'adresse) et surtout à écrire le
courrier d'adressage, qui est une vraie lettre et a donc besoin d'une adresse postale.

Deux natures, et c'est la distinction qui structure la table : un **praticien** a une
civilité, un prénom et une spécialité ; une **structure** (CHU, service hospitalier) n'a
rien de tout cela, et la lettre ne lui dit pas « Chère Consœur ».

Les spécialités tiennent dans leur propre table : trois sont connues d'avance dans le
code (Omnipraticien, ODF, CMF), le praticien ajoute les siennes depuis les Paramètres.
Le correspondant garde son libellé en toutes lettres plutôt qu'une clé étrangère :
renommer une spécialité ne doit pas réécrire les correspondants.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-21 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "correspondents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="practitioner"),
        sa.Column("title", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(length=200), nullable=False),
        sa.Column("first_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("specialty", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("practice", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("kind in ('practitioner', 'organisation')", name="correspondent_kind"),
    )
    op.create_index("ix_correspondents_organization_id", "correspondents", ["organization_id"])

    op.create_table(
        "correspondent_specialties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("organization_id", "label", name="uq_correspondent_specialty_label"),
    )
    op.create_index(
        "ix_correspondent_specialties_organization_id",
        "correspondent_specialties",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_correspondent_specialties_organization_id", table_name="correspondent_specialties"
    )
    op.drop_table("correspondent_specialties")
    op.drop_index("ix_correspondents_organization_id", table_name="correspondents")
    op.drop_table("correspondents")
