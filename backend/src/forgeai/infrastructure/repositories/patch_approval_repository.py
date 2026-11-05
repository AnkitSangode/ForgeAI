from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.repositories.patch_approval_repository import (
    PatchApprovalRepository,
)
from forgeai.execution.approval import (
    ApprovalStatus,
    PatchApproval,
)
from forgeai.infrastructure.models.patch_approval import (
    PatchApprovalModel,
)


class SQLAlchemyPatchApprovalRepository(PatchApprovalRepository):
    """Persists patch approval records using SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, approval: PatchApproval) -> PatchApproval:
        model = PatchApprovalModel(
            id=UUID(approval.approval_id),
            task_id=UUID(approval.task_id),
            patch_sha256=approval.patch_sha256,
            status=approval.status.value,
            approved_by=approval.approved_by,
            decided_at=approval.decided_at,
        )

        self.session.add(model)
        self.session.flush()

        return approval

    def get_by_id(
        self,
        approval_id: UUID,
    ) -> PatchApproval | None:
        statement = select(PatchApprovalModel).where(PatchApprovalModel.id == approval_id)
        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def get_by_id_for_update(
        self,
        approval_id: UUID,
    ) -> PatchApproval | None:
        statement = (
            select(PatchApprovalModel).where(PatchApprovalModel.id == approval_id).with_for_update()
        )
        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def update(self, approval: PatchApproval) -> PatchApproval:
        model = self.session.get(
            PatchApprovalModel,
            UUID(approval.approval_id),
        )

        if model is None:
            raise ValueError("Patch approval does not exist.")

        model.status = approval.status.value
        model.approved_by = approval.approved_by
        model.decided_at = approval.decided_at

        self.session.flush()

        return approval

    @staticmethod
    def _to_domain(model: PatchApprovalModel) -> PatchApproval:
        return PatchApproval(
            approval_id=str(model.id),
            task_id=str(model.task_id),
            patch_sha256=model.patch_sha256,
            status=ApprovalStatus(model.status),
            approved_by=model.approved_by,
            decided_at=model.decided_at,
        )
