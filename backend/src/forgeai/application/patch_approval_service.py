from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from forgeai.domain.agent_run import AgentRun
from forgeai.domain.patch_approval import ApprovalStatus, PatchApproval
from forgeai.domain.repositories.agent_run_repository import AgentRunRepository
from forgeai.domain.repositories.patch_approval_repository import (
    PatchApprovalRepository,
)


class ApprovalRunValidationError(ValueError):
    """Raised when an approval is associated with an invalid agent run."""


class PatchApprovalNotFoundError(LookupError):
    """Raised when the requested patch approval does not exist."""


class PatchApprovalStateError(ValueError):
    """Raised when an approval operation is invalid for its current state."""


class ApprovalAlreadyDecidedError(PatchApprovalStateError):
    """Raised when an approval has already been decided."""


class PatchApprovalService:
    def __init__(
        self,
        session: Session,
        approval_repository: PatchApprovalRepository,
        agent_run_repository: AgentRunRepository,
    ) -> None:
        self.session = session
        self.approval_repository = approval_repository
        self.agent_run_repository = agent_run_repository

    def create_approval(
        self,
        task_id: str,
        agent_run_id: str,
        patch_sha256: str,
    ) -> PatchApproval:
        """Create a pending approval associated with a specific agent run."""

        try:
            if not agent_run_id or not agent_run_id.strip():
                raise ApprovalRunValidationError("A valid agent run ID is required.")

            if not patch_sha256 or not patch_sha256.strip():
                raise ValueError("Patch SHA-256 fingerprint is required.")

            try:
                run_uuid = UUID(agent_run_id)
            except ValueError as exc:
                raise ApprovalRunValidationError("The agent run ID must be a valid UUID.") from exc

            run: AgentRun | None = self.agent_run_repository.get_by_id(run_uuid)

            if run is None:
                raise ApprovalRunValidationError("The associated agent run does not exist.")

            if run.task_id != task_id:
                raise ApprovalRunValidationError(
                    "The agent run does not belong to the supplied task."
                )

            approval = PatchApproval(
                approval_id=str(uuid4()),
                task_id=task_id,
                agent_run_id=agent_run_id,
                patch_sha256=patch_sha256,
                status=ApprovalStatus.PENDING,
                approved_by=None,
                decided_at=None,
                consumed_at=None,
            )

            created_approval = self.approval_repository.create(approval)
            self.session.commit()

            return created_approval

        except Exception:
            self.session.rollback()
            raise

    def decide_approval(
        self,
        approval_id: str,
        approved: bool,
        actor_id: str,
    ) -> PatchApproval:
        """Persist a reviewer's approval or rejection decision."""

        try:
            if not actor_id or not actor_id.strip():
                raise ValueError("A valid reviewer ID is required.")

            approval = self._get_approval_or_raise(approval_id)

            if approval.status != ApprovalStatus.PENDING:
                raise ApprovalAlreadyDecidedError("This approval has already been decided.")

            updated_approval = replace(
                approval,
                status=(ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED),
                approved_by=actor_id,
                decided_at=datetime.now(UTC),
            )

            result = self.approval_repository.update(updated_approval)
            self.session.commit()

            return result

        except Exception:
            self.session.rollback()
            raise

    def consume_approval(
        self,
        approval_id: str,
        task_id: str,
        agent_run_id: str,
        patch_sha256: str,
    ) -> PatchApproval:
        """
        Mark an approved patch authorization as consumed.

        The approval must match the task, agent run, and exact patch
        fingerprint. This prevents approval reuse for a different patch.
        """

        try:
            approval = self._get_approval_or_raise(approval_id)

            if approval.task_id != task_id:
                raise PatchApprovalStateError("Approval does not belong to the supplied task.")

            if approval.agent_run_id != agent_run_id:
                raise PatchApprovalStateError("Approval does not belong to the supplied agent run.")

            if approval.patch_sha256 != patch_sha256:
                raise PatchApprovalStateError(
                    "The patch fingerprint does not match the approved patch."
                )

            if approval.status != ApprovalStatus.APPROVED:
                raise PatchApprovalStateError("Only approved patches can be consumed.")

            if approval.consumed_at is not None:
                raise PatchApprovalStateError("This approval has already been consumed.")

            updated_approval = replace(
                approval,
                consumed_at=datetime.now(UTC),
            )

            result = self.approval_repository.update(updated_approval)
            self.session.commit()

            return result

        except Exception:
            self.session.rollback()
            raise

    def get_approval(self, approval_id: str) -> PatchApproval:
        """Retrieve an approval by its ID."""

        return self._get_approval_or_raise(approval_id)

    def _get_approval_or_raise(self, approval_id: str) -> PatchApproval:
        try:
            approval_uuid = UUID(approval_id)
        except ValueError as exc:
            raise PatchApprovalNotFoundError("Invalid approval ID.") from exc

        approval = self.approval_repository.get_by_id(approval_uuid)

        if approval is None:
            raise PatchApprovalNotFoundError("Patch approval does not exist.")

        return approval
