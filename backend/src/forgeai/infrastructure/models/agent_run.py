from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeai.infrastructure.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    __table_args__ = (
        CheckConstraint(
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
        Index("ix_agent_runs_task_id", "task_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )

    thread_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
