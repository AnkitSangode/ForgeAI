"""create patch executions table

Revision ID: 5c1f2a9d7e31
Revises: 4e4a7d1e057f
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c1f2a9d7e31"
down_revision: str | Sequence[str] | None = "4e4a7d1e057f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patch_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("patch_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sandbox_id", sa.String(length=255), nullable=True),
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
        sa.Column("claim_token", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'claimed', 'running', 'succeeded', 'failed')",
            name="ck_patch_executions_status",
        ),
        sa.ForeignKeyConstraint(["approval_id"], ["patch_approvals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_id", name="uq_patch_executions_approval_id"),
    )
    op.create_index(
        "ix_patch_executions_agent_run_id",
        "patch_executions",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_patch_executions_status_lease",
        "patch_executions",
        ["status", "lease_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_patch_executions_status_lease", table_name="patch_executions")
    op.drop_index("ix_patch_executions_agent_run_id", table_name="patch_executions")
    op.drop_table("patch_executions")
