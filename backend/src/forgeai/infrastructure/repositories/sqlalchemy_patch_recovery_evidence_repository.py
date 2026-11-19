
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.patch_recovery_evidence import PatchRecoveryEvidence
from forgeai.domain.repositories.patch_recovery_evidence_repository import (
    PatchRecoveryEvidenceRepository,
)
from forgeai.infrastructure.models.patch_recovery_evidence import (
    PatchRecoveryEvidenceModel,
)


class SQLAlchemyPatchRecoveryEvidenceRepository(
    PatchRecoveryEvidenceRepository
):

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        evidence: PatchRecoveryEvidence,
    ) -> PatchRecoveryEvidence:
        model = PatchRecoveryEvidenceModel(
            id=UUID(evidence.evidence_id),
            execution_id=UUID(evidence.execution_id),
            sandbox_id=evidence.sandbox_id,
            patch_sha256=evidence.patch_sha256,
            disposition=evidence.disposition,
            reason=evidence.reason,
            observed_files=list(evidence.observed_files),
            worker_stopped=evidence.worker_stopped,
            inspected_at=evidence.inspected_at,
        )

        self.session.add(model)
        self.session.flush()

        return self._to_domain(model)

    def get_by_execution_id(
        self,
        execution_id: UUID,
    ) -> list[PatchRecoveryEvidence]:
        statement = (
            select(PatchRecoveryEvidenceModel)
            .where(PatchRecoveryEvidenceModel.execution_id == execution_id)
            .order_by(PatchRecoveryEvidenceModel.inspected_at)
        )

        return [
            self._to_domain(model)
            for model in self.session.scalars(statement).all()
        ]

    @staticmethod
    def _to_domain(
        model: PatchRecoveryEvidenceModel,
    ) -> PatchRecoveryEvidence:
        return PatchRecoveryEvidence(
            evidence_id=str(model.id),
            execution_id=str(model.execution_id),
            sandbox_id=model.sandbox_id,
            patch_sha256=model.patch_sha256,
            disposition=model.disposition,
            reason=model.reason,
            observed_files=tuple(model.observed_files),
            worker_stopped=model.worker_stopped,
            inspected_at=model.inspected_at,
        )
