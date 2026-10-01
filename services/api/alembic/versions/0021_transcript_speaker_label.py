"""La voix d'où vient chaque passage, telle que la transcription l'a séparée.

Le rôle (praticien, patient) se décide à partir de ces voix. Le garder permet de
rejuger l'attribution sans refaire la transcription — l'audio, lui, est déjà effacé —
et de savoir, quand tout reste « inconnu », si la séparation des voix a même eu lieu.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-26 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transcript_segments",
        sa.Column("speaker_label", sa.String(length=32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("transcript_segments", "speaker_label")
