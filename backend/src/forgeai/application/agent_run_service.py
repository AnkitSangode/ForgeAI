from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from forgeai.domain.agent_run import AgentRun, AgentRunStatus
from forgeai.domain.repositories.agent_run_repository import (
    AgentRunRepository,
)
from forgeai.infrastructure.repositories.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)


class AgentRunNotFoundError(Exception):
    pass


class InvalidAgentRunTransitionError(ValueError):
    """Raised when an agent run attempts an invalid status transition."""


class AgentRunService:

    ALLOWED_TRANSITIONS = {
        AgentRunStatus.PENDING: {
            AgentRunStatus.RUNNING,
            AgentRunStatus.FAILED,
        },
        AgentRunStatus.RUNNING: {
            AgentRunStatus.AWAITING_APPROVAL,
            AgentRunStatus.REJECTED,
            AgentRunStatus.FAILED,
        },
        AgentRunStatus.AWAITING_APPROVAL: {
            AgentRunStatus.EXECUTING,
            AgentRunStatus.REJECTED,
            AgentRunStatus.FAILED,
        },
        AgentRunStatus.EXECUTING: {
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.FAILED,
        },
        AgentRunStatus.SUCCEEDED: set(),
        AgentRunStatus.REJECTED: set(),
        AgentRunStatus.FAILED: set(),
    }

    def __init__(
        self,
        session: Session,
        repository: AgentRunRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or SQLAlchemyAgentRunRepository(session)

    def create_run(self, task_id: str) -> AgentRun:
        run_id = uuid4()
        now = datetime.now(UTC)

        run = AgentRun(
            id=str(run_id),
            task_id=task_id,
            thread_id=str(run_id),
            status=AgentRunStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        try:
            self.repository.create(run)
            self.session.commit()
            return run
        except Exception:
            self.session.rollback()
            raise

    def get_run(self, run_id: str) -> AgentRun:
        run = self.repository.get_by_id(UUID(run_id))

        if run is None:
            raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found.")

        return run

    def get_run_by_thread_id(self, thread_id: str) -> AgentRun | None:
        return self.repository.get_by_thread_id(thread_id)

    def update_status(
        self,
        run_id: str,
        status: AgentRunStatus,
    ) -> AgentRun:
        try:
            run = self.repository.get_by_id(UUID(run_id))

            if run is None:
                raise AgentRunNotFoundError(f"Agent run '{run_id}' was not found.")

            # Allow an idempotent request without another database write.
            if run.status == status:
                return run

            allowed_statuses = self.ALLOWED_TRANSITIONS[run.status]

            if status not in allowed_statuses:
                raise InvalidAgentRunTransitionError(
                    f"Cannot transition agent run from "
                    f"'{run.status.value}' to '{status.value}'."
                )

            updated_run = replace(
                run,
                status=status,
                updated_at=datetime.now(UTC),
            )

            self.repository.update(updated_run)
            self.session.commit()

            return updated_run

        except Exception:
            self.session.rollback()
            raise
