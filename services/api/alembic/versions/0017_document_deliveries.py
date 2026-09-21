"""Noter à qui un document a été envoyé.

Oris n'envoie rien : le praticien envoie le compte rendu par mail, par courrier ou le
remet en main propre, puis le **note** dans Oris. La liste des consultations peut alors
dire « envoyé au Dr Martin » au lieu de laisser deviner.

Le nom du destinataire est recopié au moment du geste : supprimer un correspondant plus
tard ne doit pas effacer la trace de ce qui lui a été envoyé.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-21 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_kind", sa.String(length=20), nullable=False),
        sa.Column(
            "correspondent_id",
            sa.Uuid(),
            sa.ForeignKey("correspondents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_label", sa.String(length=200), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "recipient_kind in ('patient', 'correspondent', 'other')",
            name="document_delivery_recipient_kind",
        ),
        sa.CheckConstraint(
            "channel in ('email', 'mail', 'hand', 'secure_messaging', 'other')",
            name="document_delivery_channel",
        ),
    )
    for colonne in ("organization_id", "document_id", "correspondent_id"):
        op.create_index(f"ix_document_deliveries_{colonne}", "document_deliveries", [colonne])


def downgrade() -> None:
    for colonne in ("correspondent_id", "document_id", "organization_id"):
        op.drop_index(f"ix_document_deliveries_{colonne}", table_name="document_deliveries")
    op.drop_table("document_deliveries")
