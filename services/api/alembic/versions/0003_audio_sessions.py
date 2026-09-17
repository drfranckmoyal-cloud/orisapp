"""Sessions et segments audio : métadonnées de capture, sans le son (M2).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17 04:54:49.800455
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audio_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "finalized",
                name="audio_session_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("audio_format", sa.String(length=100), nullable=False),
        sa.Column("final_sequence", sa.Integer(), nullable=True),
        sa.Column("client_recorded_ms", sa.Integer(), nullable=True),
        sa.Column("reported_gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "purge_status",
            sa.Enum(
                "retained",
                "purged",
                name="audio_purge_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["encounter_id"],
            ["encounters.id"],
            name=op.f("fk_audio_sessions_encounter_id_encounters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audio_sessions")),
        sa.UniqueConstraint("encounter_id", name=op.f("uq_audio_sessions_encounter_id")),
    )
    op.create_table(
        "audio_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audio_session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 0", name=op.f("ck_audio_chunks_sequence_positive")),
        sa.CheckConstraint(
            "timestamp_ms >= 0 AND duration_ms > 0", name=op.f("ck_audio_chunks_timing_valid")
        ),
        sa.ForeignKeyConstraint(
            ["audio_session_id"],
            ["audio_sessions.id"],
            name=op.f("fk_audio_chunks_audio_session_id_audio_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audio_chunks")),
        sa.UniqueConstraint("audio_session_id", "sequence", name="uq_audio_chunks_sequence"),
    )
    op.create_index(
        op.f("ix_audio_chunks_audio_session_id"), "audio_chunks", ["audio_session_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audio_chunks_audio_session_id"), table_name="audio_chunks")
    op.drop_table("audio_chunks")
    op.drop_table("audio_sessions")
