from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from forgeai.domain.patch_approval import (
    ApprovalStatus,
    PatchApproval,
)
from forgeai.domain.repositories.patch_approval_repository import (
    PatchApprovalRepository,
)
from forgeai.infrastructure.repositories.patch_approval_repository import (
    SQLAlchemyPatchApprovalRepository,
)


class ApprovalNotFoundError(Exception):
    """Raised when an approval request does not exist."""


class ApprovalAlreadyDecidedError(Exception):
    """Raised when an approval has already been decided."""


class ApprovalConsumptionError(Exception):
    """Raised when an approval cannot authorize patch execution."""


class PatchApprovalService:
    """Coordinates patch approval operations and database transactions."""

    def __init__(
        self,
        session: Session,
        repository: PatchApprovalRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or SQLAlchemyPatchApprovalRepository(session)

    def create_approval(
        self,
        task_id: str,
        patch_sha256: str,
    ) -> PatchApproval:
        """Create a pending approval request for a specific patch."""

        approval = PatchApproval(
            approval_id=str(uuid4()),
            task_id=task_id,
            patch_sha256=patch_sha256,
            status=ApprovalStatus.PENDING,
            approved_by=None,
            decided_at=None,
            consumed_at=None,
        )

        try:
            self.repository.create(approval)
            self.session.commit()
            return approval

        except Exception:
            self.session.rollback()
            raise

    def decide_approval(
        self,
        approval_id: str,
        approved: bool,
        actor_id: str,
    ) -> PatchApproval:
        """Record an authenticated human's decision on a pending approval."""

        try:
            if not actor_id or not actor_id.strip():
                raise ValueError("A valid actor ID is required.")

            approval = self.repository.get_by_id_for_update(UUID(approval_id))

            if approval is None:
                raise ApprovalNotFoundError(f"Approval {approval_id} was not found.")

            if approval.status != ApprovalStatus.PENDING:
                raise ApprovalAlreadyDecidedError("This approval has already been decided.")

            updated_approval = replace(
                approval,
                status=(ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED),
                approved_by=actor_id,
                decided_at=datetime.now(UTC),
            )

            self.repository.update(updated_approval)
            self.session.commit()

            return updated_approval

        except Exception:
            self.session.rollback()
            raise

    def consume_approval(
        self,
        approval_id: str,
        task_id: str,
        patch_sha256: str,
    ) -> PatchApproval:
        """Atomically consume an approval for one exact patch."""

        try:
            approval = self.repository.get_by_id_for_update(UUID(approval_id))

            if approval is None:
                raise ApprovalConsumptionError("Approval cannot authorize this execution.")

            if approval.task_id != task_id:
                raise ApprovalConsumptionError("Approval cannot authorize this execution.")

            if approval.patch_sha256 != patch_sha256:
                raise ApprovalConsumptionError("Approval cannot authorize this execution.")

            if approval.status != ApprovalStatus.APPROVED:
                raise ApprovalConsumptionError("Approval cannot authorize this execution.")

            if approval.consumed_at is not None:
                raise ApprovalConsumptionError("Approval cannot authorize this execution.")

            consumed_approval = replace(
                approval,
                consumed_at=datetime.now(UTC),
            )

            self.repository.update(consumed_approval)
            self.session.commit()

            return consumed_approval

        except Exception:
            self.session.rollback()
            raise

    def get_approval(self, approval_id: str) -> PatchApproval:
        """Retrieve an approval by its ID."""

        approval = self.repository.get_by_id(UUID(approval_id))

        if approval is None:
            raise ApprovalNotFoundError(f"Approval {approval_id} was not found.")

        return approval
