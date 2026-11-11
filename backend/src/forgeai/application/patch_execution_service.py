
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forgeai.application.patch_approval_service import (
    PatchApprovalService,
    PatchApprovalStateError,
)
from forgeai.domain.patch_execution import (
    PatchExecution,
    PatchExecutionStatus,
)
from forgeai.domain.repositories.patch_execution_repository import (
    PatchExecutionRepository,
)


class PatchExecutionNotFoundError(LookupError):
    """Raised when a patch execution does not exist."""


class PatchExecutionStateError(ValueError):
    """Raised when an execution operation is invalid."""


class PatchExecutionService:
    def __init__(
        self,
        session: Session,
        execution_repository: PatchExecutionRepository,
        approval_service: PatchApprovalService,
    ) -> None:
        self.session = session
        self.execution_repository = execution_repository
        self.approval_service = approval_service

    def create_execution(
        self,
        approval_id: str,
        task_id: str,
        agent_run_id: str,
        patch_sha256: str,
    ) -> PatchExecution:
        """
        Consume an approved patch and create its execution record
        in one database transaction.

        Repeated requests for the same approval return the existing
        execution record.
        """

        try:
            approval_uuid = UUID(approval_id)
            task_uuid = UUID(task_id)
            run_uuid = UUID(agent_run_id)

            # Lock the approval row before checking for an existing
            # execution. This serializes concurrent creation attempts
            # for the same approval.
            approval = (
                self.approval_service.approval_repository
                .get_by_id_for_update(approval_uuid)
            )

            if approval is None:
                raise PatchExecutionStateError(
                    "The associated approval does not exist."
                )

            # Validate the identity of the approval before returning
            # an existing execution.
            if UUID(approval.task_id) != task_uuid:
                raise PatchExecutionStateError(
                    "Approval does not belong to the supplied task."
                )

            if approval.agent_run_id is None:
                raise PatchExecutionStateError(
                    "Approval is not associated with an agent run."
                )

            if UUID(approval.agent_run_id) != run_uuid:
                raise PatchExecutionStateError(
                    "Approval does not belong to the supplied agent run."
                )

            if approval.patch_sha256 != patch_sha256:
                raise PatchExecutionStateError(
                    "Patch fingerprint does not match the approval."
                )

            # Idempotency: if execution was already created, return it.
            existing_execution = (
                self.execution_repository.get_by_approval_id(
                    approval_uuid
                )
            )

            if existing_execution is not None:
                if (
                    existing_execution.patch_sha256 != patch_sha256
                    or UUID(existing_execution.task_id) != task_uuid
                    or UUID(existing_execution.agent_run_id) != run_uuid
                ):
                    raise PatchExecutionStateError(
                        "Existing execution does not match the supplied "
                        "approval details."
                    )

                self.session.rollback()
                return existing_execution

            # Consume approval without committing independently.
            self.approval_service.consume_approval_in_transaction(
                approval_id=approval_id,
                task_id=task_id,
                agent_run_id=agent_run_id,
                patch_sha256=patch_sha256,
            )

            execution = PatchExecution(
                execution_id=str(uuid4()),
                approval_id=approval_id,
                task_id=task_id,
                agent_run_id=agent_run_id,
                patch_sha256=patch_sha256,
                status=PatchExecutionStatus.PENDING,
                sandbox_id=None,
                claimed_by=None,
                claim_token=None,
                lease_expires_at=None,
                claimed_at=None,
                started_at=None,
                completed_at=None,
                error=None,
            )

            created_execution = self.execution_repository.create(
                execution
            )

            # Both approval consumption and execution creation are
            # committed together.
            self.session.commit()

            return created_execution

        except IntegrityError:
            self.session.rollback()

            # A unique-constraint conflict can occur if another
            # transaction created the execution concurrently.
            existing_execution = None

            try:
                existing_execution = (
                    self.execution_repository.get_by_approval_id(
                        UUID(approval_id)
                    )
                )
            except Exception:
                self.session.rollback()
                raise

            if existing_execution is not None:
                if (
                    existing_execution.patch_sha256 == patch_sha256
                    and UUID(existing_execution.task_id) == UUID(task_id)
                    and UUID(existing_execution.agent_run_id)
                    == UUID(agent_run_id)
                ):
                    return existing_execution

            raise

        except Exception:
            self.session.rollback()
            raise

    def get_execution(
        self,
        execution_id: str,
    ) -> PatchExecution:
        """Retrieve an execution by its ID."""

        try:
            execution_uuid = UUID(execution_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise PatchExecutionNotFoundError(
                "Invalid execution ID."
            ) from exc

        execution = self.execution_repository.get_by_id(
            execution_uuid
        )

        if execution is None:
            raise PatchExecutionNotFoundError(
                "Patch execution does not exist."
            )

        return execution
