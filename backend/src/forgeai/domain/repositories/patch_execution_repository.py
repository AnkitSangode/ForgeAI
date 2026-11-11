
from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.domain.patch_execution import PatchExecution


class PatchExecutionRepository(ABC):

    @abstractmethod
    def create(
        self,
        execution: PatchExecution,
    ) -> PatchExecution:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        execution_id: UUID,
    ) -> PatchExecution | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_approval_id(
        self,
        approval_id: UUID,
    ) -> PatchExecution | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id_for_update(
        self,
        execution_id: UUID,
    ) -> PatchExecution | None:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        execution: PatchExecution,
    ) -> PatchExecution:
        raise NotImplementedError
