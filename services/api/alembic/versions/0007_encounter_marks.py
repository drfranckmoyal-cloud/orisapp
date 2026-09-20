"""Points marqués pendant l'écoute (spec §11).

Un point marqué est un repère temporel, jamais un fait clinique : il aide le
praticien à retrouver un moment dans la transcription, et n'entre pas dans
l'objet clinique.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-20 21:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "encounter_marks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "encounter_id",
            sa.Uuid(),
            sa.ForeignKey("encounters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("timestamp_ms >= 0", name="mark_timestamp_positive"),
        sa.UniqueConstraint("encounter_id", "timestamp_ms", name="uq_encounter_marks_moment"),
    )


def downgrade() -> None:
    op.drop_table("encounter_marks")
