from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.domain.agent_run import AgentRun


class AgentRunRepository(ABC):
    @abstractmethod
    def create(self, run: AgentRun) -> AgentRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_thread_id(self, thread_id: str) -> AgentRun | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, run: AgentRun) -> AgentRun:
        raise NotImplementedError

    @abstractmethod
    def get_by_id_for_update(self, run_id: UUID) -> AgentRun | None:
        """Retrieve and lock an agent run for a transactional update."""
        raise NotImplementedError