"""add agent runs table

Revision ID: db8ba4a8aa16
Revises: fdc1b6d0776e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "db8ba4a8aa16"
down_revision: str | Sequence[str] | None = "fdc1b6d0776e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            """
            status IN (
                'pending',
                'running',
                'awaiting_approval',
                'executing',
                'succeeded',
                'rejected',
                'failed'
            )
            """,
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )

    op.create_index(
        "ix_agent_runs_task_id",
        "agent_runs",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_runs_task_id",
        table_name="agent_runs",
    )
    op.drop_table("agent_runs")
