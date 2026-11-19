
"""add durable patch execution evidence

Revision ID: 7d2a6c9e4f10
Revises: 5c1f2a9d7e31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d2a6c9e4f10"
down_revision: str | Sequence[str] | None = "5c1f2a9d7e31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patch_test_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("patch_sha256", sa.String(64), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["patch_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id",
            "attempt_id",
            "sequence_number",
            name="uq_patch_test_evidence_attempt_sequence",
        ),
    )

    op.create_index(
        "ix_patch_test_evidence_execution",
        "patch_test_evidence",
        ["execution_id"],
    )

    op.create_table(
        "patch_recovery_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("sandbox_id", sa.String(255), nullable=True),
        sa.Column("patch_sha256", sa.String(64), nullable=False),
        sa.Column("disposition", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("observed_files", sa.JSON(), nullable=False),
        sa.Column("worker_stopped", sa.Boolean(), nullable=False),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["patch_executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_patch_recovery_evidence_execution",
        "patch_recovery_evidence",
        ["execution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patch_recovery_evidence_execution",
        table_name="patch_recovery_evidence",
    )
    op.drop_table("patch_recovery_evidence")

    op.drop_index(
        "ix_patch_test_evidence_execution",
        table_name="patch_test_evidence",
    )
    op.drop_table("patch_test_evidence")
