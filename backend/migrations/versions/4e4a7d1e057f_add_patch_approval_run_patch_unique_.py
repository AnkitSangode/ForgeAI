
"""add_patch_approval_run_patch_unique_constraint

Revision ID: 4e4a7d1e057f
Revises: 80dfa58a654c
Create Date: 2026-11-11 13:29:35.702430
"""

from typing import Sequence, Union

from alembic import op


revision: str = "4e4a7d1e057f"
down_revision: Union[str, Sequence[str], None] = "80dfa58a654c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add uniqueness for an approval per run and patch."""

    op.create_unique_constraint(
        "uq_patch_approvals_run_patch",
        "patch_approvals",
        ["agent_run_id", "patch_sha256"],
    )


def downgrade() -> None:
    """Remove the approval uniqueness constraint."""

    op.drop_constraint(
        "uq_patch_approvals_run_patch",
        "patch_approvals",
        type_="unique",
    )
