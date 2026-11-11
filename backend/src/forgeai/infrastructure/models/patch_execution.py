
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeai.infrastructure.base import Base


class PatchExecutionModel(Base):
    __tablename__ = "patch_executions"

    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'pending',
                'claimed',
                'running',
                'succeeded',
                'failed'
            )
            """,
            name="ck_patch_executions_status",
        ),
        UniqueConstraint(
            "approval_id",
            name="uq_patch_executions_approval_id",
        ),
        Index(
            "ix_patch_executions_agent_run_id",
            "agent_run_id",
        ),
        Index(
            "ix_patch_executions_status_lease",
            "status",
            "lease_expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    approval_id: Mapped[UUID] = mapped_column(
        ForeignKey("patch_approvals.id", ondelete="CASCADE"),
        nullable=False,
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    patch_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    sandbox_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    claimed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    claim_token: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
