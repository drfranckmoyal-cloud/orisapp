"""Les photos de la « Documentation clinique » d'un document.

Les modèles du praticien finissent par une page de photographies légendées, toujours
sur une page à part et sans rien de clinique après. Le document cite des pièces jointes
du patient : la photo n'est pas copiée, et supprimer la pièce la retire du document.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-21 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_figures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            sa.Uuid(),
            sa.ForeignKey("attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("caption", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("document_id", "attachment_id", name="uq_document_figure_pair"),
    )
    op.create_index("ix_document_figures_document_id", "document_figures", ["document_id"])
    op.create_index("ix_document_figures_attachment_id", "document_figures", ["attachment_id"])


def downgrade() -> None:
    op.drop_index("ix_document_figures_attachment_id", table_name="document_figures")
    op.drop_index("ix_document_figures_document_id", table_name="document_figures")
    op.drop_table("document_figures")
