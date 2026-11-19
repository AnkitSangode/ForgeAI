
from abc import ABC, abstractmethod
from uuid import UUID

from forgeai.domain.patch_recovery_evidence import PatchRecoveryEvidence


class PatchRecoveryEvidenceRepository(ABC):

    @abstractmethod
    def create(
        self,
        evidence: PatchRecoveryEvidence,
    ) -> PatchRecoveryEvidence:
        raise NotImplementedError

    @abstractmethod
    def get_by_execution_id(
        self,
        execution_id: UUID,
    ) -> list[PatchRecoveryEvidence]:
        raise NotImplementedError
