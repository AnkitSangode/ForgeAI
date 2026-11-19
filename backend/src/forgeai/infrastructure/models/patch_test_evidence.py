
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeai.infrastructure.base import Base


class PatchTestEvidenceModel(Base):
    __tablename__ = "patch_test_evidence"

    __table_args__ = (
        UniqueConstraint(
            "execution_id",
            "attempt_id",
            "sequence_number",
            name="uq_patch_test_evidence_attempt_sequence",
        ),
        Index(
            "ix_patch_test_evidence_execution",
            "execution_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("patch_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    attempt_id: Mapped[UUID] = mapped_column(nullable=False)

    patch_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    command: Mapped[str] = mapped_column(Text, nullable=False)

    exit_code: Mapped[int] = mapped_column(Integer, nullable=False)

    stdout: Mapped[str] = mapped_column(Text, nullable=False, default="")

    stderr: Mapped[str] = mapped_column(Text, nullable=False, default="")

    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
