from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.execution.approval import PatchApproval


class PatchApprovalRepository(ABC):
    @abstractmethod
    def create(self, approval: PatchApproval) -> PatchApproval:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        approval_id: UUID,
    ) -> PatchApproval | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_id_for_update(
        self,
        approval_id: UUID,
    ) -> PatchApproval | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, approval: PatchApproval) -> PatchApproval:
        raise NotImplementedError
