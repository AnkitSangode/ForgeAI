"""add user roles

Revision ID: fdc1b6d0776e
Revises: db7b6baab016
Create Date: 2026-11-06 11:15:01.940207

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fdc1b6d0776e'
down_revision: str | Sequence[str] | None = 'db7b6baab016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")