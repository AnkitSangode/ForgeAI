
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.patch_test_evidence import PatchTestEvidence
from forgeai.domain.repositories.patch_test_evidence_repository import (
    PatchTestEvidenceRepository,
)
from forgeai.infrastructure.models.patch_test_evidence import (
    PatchTestEvidenceModel,
)


class SQLAlchemyPatchTestEvidenceRepository(PatchTestEvidenceRepository):

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, evidence: PatchTestEvidence) -> PatchTestEvidence:
        model = PatchTestEvidenceModel(
            id=UUID(evidence.evidence_id),
            execution_id=UUID(evidence.execution_id),
            attempt_id=UUID(evidence.attempt_id),
            patch_sha256=evidence.patch_sha256,
            sequence_number=evidence.sequence_number,
            command=evidence.command,
            exit_code=evidence.exit_code,
            stdout=evidence.stdout,
            stderr=evidence.stderr,
            timed_out=evidence.timed_out,
            started_at=evidence.started_at,
            completed_at=evidence.completed_at,
        )

        self.session.add(model)
        self.session.flush()

        return self._to_domain(model)

    def get_by_execution_id(
        self,
        execution_id: UUID,
    ) -> list[PatchTestEvidence]:
        statement = (
            select(PatchTestEvidenceModel)
            .where(PatchTestEvidenceModel.execution_id == execution_id)
            .order_by(
                PatchTestEvidenceModel.attempt_id,
                PatchTestEvidenceModel.sequence_number,
            )
        )

        return [
            self._to_domain(model)
            for model in self.session.scalars(statement).all()
        ]

    @staticmethod
    def _to_domain(model: PatchTestEvidenceModel) -> PatchTestEvidence:
        return PatchTestEvidence(
            evidence_id=str(model.id),
            execution_id=str(model.execution_id),
            attempt_id=str(model.attempt_id),
            patch_sha256=model.patch_sha256,
            sequence_number=model.sequence_number,
            command=model.command,
            exit_code=model.exit_code,
            stdout=model.stdout,
            stderr=model.stderr,
            timed_out=model.timed_out,
            started_at=model.started_at,
            completed_at=model.completed_at,
        )
