import hmac
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forgeai.application.patch_approval_service import (
    PatchApprovalService,
)
from forgeai.domain.agent_run import AgentRunStatus
from forgeai.domain.patch_execution import (
    PatchExecution,
    PatchExecutionStatus,
)
from forgeai.domain.repositories.agent_run_repository import (
    AgentRunRepository,
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
        agent_run_repository: AgentRunRepository,
    ) -> None:
        self.session = session
        self.execution_repository = execution_repository
        self.approval_service = approval_service
        self.agent_run_repository = agent_run_repository

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

    def claim_execution(
        self,
        execution_id: str,
        worker_id: str,
        lease_seconds: int = 300,
    ) -> PatchExecution:
        """
        Atomically claim a pending execution.

        Locks the execution and associated AgentRun, updates both
        records using the same SQLAlchemy session, and commits once.

        Expired claims are deliberately not reclaimed automatically.
        The sandbox must first be reconciled before retrying external
        side effects.
        """

        if not isinstance(worker_id, str) or not worker_id.strip():
            raise PatchExecutionStateError(
                "Worker ID cannot be blank."
            )

        if (
            not isinstance(lease_seconds, int)
            or isinstance(lease_seconds, bool)
            or lease_seconds <= 0
        ):
            raise PatchExecutionStateError(
                "Lease duration must be a positive integer."
            )

        try:
            execution_uuid = UUID(execution_id)

            # Lock the execution row first.
            execution = (
                self.execution_repository.get_by_id_for_update(
                    execution_uuid
                )
            )

            if execution is None:
                raise PatchExecutionNotFoundError(
                    "Patch execution does not exist."
                )

            if execution.status != PatchExecutionStatus.PENDING:
                raise PatchExecutionStateError(
                    "Execution cannot be claimed from status: "
                    f"{execution.status.value}."
                )

            # Lock the associated AgentRun.
            agent_run_uuid = UUID(execution.agent_run_id)

            agent_run = (
                self.agent_run_repository.get_by_id_for_update(
                    agent_run_uuid
                )
            )

            if agent_run is None:
                raise PatchExecutionStateError(
                    "Associated agent run does not exist."
                )

            if UUID(agent_run.task_id) != UUID(execution.task_id):
                raise PatchExecutionStateError(
                    "Agent run does not belong to the execution task."
                )

            if agent_run.status != AgentRunStatus.AWAITING_APPROVAL:
                raise PatchExecutionStateError(
                    "Agent run is not awaiting human approval."
                )

            now = datetime.now(UTC)

            claimed_execution = replace(
                execution,
                status=PatchExecutionStatus.CLAIMED,
                claimed_by=worker_id.strip(),
                claim_token=secrets.token_urlsafe(32),
                claimed_at=now,
                lease_expires_at=now + timedelta(
                    seconds=lease_seconds
                ),
            )

            executing_run = replace(
                agent_run,
                status=AgentRunStatus.EXECUTING,
                updated_at=now,
            )

            # Both repositories must share this service's session.
            updated_execution = self.execution_repository.update(
                claimed_execution
            )

            self.agent_run_repository.update(executing_run)

            # Commit both state changes atomically.
            self.session.commit()

            return updated_execution

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

    
    def _get_execution_for_claimed_worker(
        self,
        execution_id: str,
        claim_token: str,
        allowed_statuses: set[PatchExecutionStatus],
    ) -> tuple[PatchExecution, object]:
        """Lock execution and verify worker ownership and lifecycle state."""

        if not isinstance(claim_token, str) or not claim_token:
            raise PatchExecutionStateError(
                "A valid claim token is required."
            )

        execution_uuid = UUID(execution_id)

        execution = self.execution_repository.get_by_id_for_update(
            execution_uuid
        )

        if execution is None:
            raise PatchExecutionNotFoundError(
                "Patch execution does not exist."
            )

        if (
            execution.claim_token is None
            or not hmac.compare_digest(
                execution.claim_token,
                claim_token,
            )
        ):
            raise PatchExecutionStateError(
                "Claim token is invalid or does not belong to this worker."
            )

        if execution.status not in allowed_statuses:
            raise PatchExecutionStateError(
                f"Operation is not allowed from status: "
                f"{execution.status.value}."
            )

        agent_run = self.agent_run_repository.get_by_id_for_update(
            UUID(execution.agent_run_id)
        )

        if agent_run is None:
            raise PatchExecutionStateError(
                "Associated agent run does not exist."
            )

        if UUID(agent_run.task_id) != UUID(execution.task_id):
            raise PatchExecutionStateError(
                "Agent run does not belong to the execution task."
            )

        return execution, agent_run

    def start_execution(
        self,
        execution_id: str,
        claim_token: str,
    ) -> PatchExecution:
        """Move a claimed execution into the running state."""

        try:
            execution, agent_run = self._get_execution_for_claimed_worker(
                execution_id,
                claim_token,
                {PatchExecutionStatus.CLAIMED},
            )

            if agent_run.status != AgentRunStatus.EXECUTING:
                raise PatchExecutionStateError(
                    "Agent run is not in the executing state."
                )

            updated_execution = replace(
                execution,
                status=PatchExecutionStatus.RUNNING,
                started_at=datetime.now(UTC),
            )

            result = self.execution_repository.update(updated_execution)
            self.session.commit()

            return result

        except Exception:
            self.session.rollback()
            raise

    def complete_execution(
        self,
        execution_id: str,
        claim_token: str,
        sandbox_id: str | None = None,
    ) -> PatchExecution:
        """
        Mark an execution successful after patch application and
        verification have completed successfully.
        """

        try:
            execution, agent_run = self._get_execution_for_claimed_worker(
                execution_id,
                claim_token,
                {PatchExecutionStatus.RUNNING},
            )

            if agent_run.status != AgentRunStatus.EXECUTING:
                raise PatchExecutionStateError(
                    "Agent run is not in the executing state."
                )

            now = datetime.now(UTC)

            updated_execution = replace(
                execution,
                status=PatchExecutionStatus.SUCCEEDED,
                sandbox_id=sandbox_id or execution.sandbox_id,
                completed_at=now,
                error=None,
            )

            updated_run = replace(
                agent_run,
                status=AgentRunStatus.SUCCEEDED,
                updated_at=now,
            )

            result = self.execution_repository.update(updated_execution)
            self.agent_run_repository.update(updated_run)

            self.session.commit()

            return result

        except Exception:
            self.session.rollback()
            raise

    def fail_execution(
        self,
        execution_id: str,
        claim_token: str,
        error: str,
    ) -> PatchExecution:
        """
        Mark an execution failed.

        A worker may report failure while CLAIMED or RUNNING, provided
        it still owns the claim token.
        """

        if not isinstance(error, str) or not error.strip():
            raise PatchExecutionStateError(
                "A failure description is required."
            )

        try:
            execution, agent_run = self._get_execution_for_claimed_worker(
                execution_id,
                claim_token,
                {
                    PatchExecutionStatus.CLAIMED,
                    PatchExecutionStatus.RUNNING,
                },
            )

            if agent_run.status != AgentRunStatus.EXECUTING:
                raise PatchExecutionStateError(
                    "Agent run is not in the executing state."
                )

            now = datetime.now(UTC)

            updated_execution = replace(
                execution,
                status=PatchExecutionStatus.FAILED,
                completed_at=now,
                error=error.strip(),
            )

            updated_run = replace(
                agent_run,
                status=AgentRunStatus.FAILED,
                updated_at=now,
            )

            result = self.execution_repository.update(updated_execution)
            self.agent_run_repository.update(updated_run)

            self.session.commit()

            return result

        except Exception:
            self.session.rollback()
            raise


