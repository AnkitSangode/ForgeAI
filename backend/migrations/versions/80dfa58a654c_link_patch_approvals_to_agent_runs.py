"""link patch approvals to agent runs

Revision ID: 80dfa58a654c
Revises: db8ba4a8aa16
Create Date: 2026-11-10 13:51:10.938037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "80dfa58a654c"
down_revision: str | Sequence[str] | None = "db8ba4a8aa16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patch_approvals",
        sa.Column(
            "agent_run_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_patch_approvals_agent_run_id",
        "patch_approvals",
        ["agent_run_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_patch_approvals_agent_run_id_agent_runs",
        "patch_approvals",
        "agent_runs",
        ["agent_run_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_patch_approvals_agent_run_id_agent_runs",
        "patch_approvals",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_patch_approvals_agent_run_id",
        table_name="patch_approvals",
    )

    op.drop_column(
        "patch_approvals",
        "agent_run_id",
    )
