
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from forgeai.infrastructure.base import Base


class PatchRecoveryEvidenceModel(Base):
    __tablename__ = "patch_recovery_evidence"

    __table_args__ = (
        Index(
            "ix_patch_recovery_evidence_execution",
            "execution_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("patch_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    sandbox_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patch_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    disposition: Mapped[str] = mapped_column(String(50), nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    observed_files: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    worker_stopped: Mapped[bool] = mapped_column(Boolean, nullable=False)

    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
