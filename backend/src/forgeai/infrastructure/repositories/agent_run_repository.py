
from dataclasses import replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.agent_run import AgentRun, AgentRunStatus
from forgeai.domain.repositories.agent_run_repository import (
    AgentRunRepository,
)
from forgeai.infrastructure.models.agent_run import AgentRun as AgentRunModel


class SQLAlchemyAgentRunRepository(AgentRunRepository):

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, run: AgentRun) -> AgentRun:
        model = AgentRunModel(
            id=UUID(run.id),
            task_id=UUID(run.task_id),
            thread_id=run.thread_id,
            status=run.status.value,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

        self.session.add(model)
        self.session.flush()

        return run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        statement = select(AgentRunModel).where(
            AgentRunModel.id == run_id
        )
        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def get_by_thread_id(self, thread_id: str) -> AgentRun | None:
        statement = select(AgentRunModel).where(
            AgentRunModel.thread_id == thread_id
        )
        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def update(self, run: AgentRun) -> AgentRun:
        model = self.session.get(AgentRunModel, UUID(run.id))

        if model is None:
            raise ValueError("Agent run does not exist.")

        model.status = run.status.value
        model.thread_id = run.thread_id
        model.updated_at = run.updated_at

        self.session.flush()

        return run

    @staticmethod
    def _to_domain(model: AgentRunModel) -> AgentRun:
        return AgentRun(
            id=str(model.id),
            task_id=str(model.task_id),
            thread_id=model.thread_id,
            status=AgentRunStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
