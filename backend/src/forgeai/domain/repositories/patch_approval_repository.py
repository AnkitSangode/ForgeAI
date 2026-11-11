
from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.domain.patch_approval import PatchApproval


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
    def get_by_run_and_patch(
        self,
        agent_run_id: UUID,
        patch_sha256: str,
    ) -> PatchApproval | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, approval: PatchApproval) -> PatchApproval:
        raise NotImplementedError
