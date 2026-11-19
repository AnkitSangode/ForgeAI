
from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.domain.patch_test_evidence import PatchTestEvidence


class PatchTestEvidenceRepository(ABC):

    @abstractmethod
    def create(self, evidence: PatchTestEvidence) -> PatchTestEvidence:
        raise NotImplementedError

    @abstractmethod
    def get_by_execution_id(
        self,
        execution_id: UUID,
    ) -> list[PatchTestEvidence]:
        raise NotImplementedError
