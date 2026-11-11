from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.patch_approval import (
    PatchApproval,
    ApprovalStatus,
)
from forgeai.domain.repositories.patch_approval_repository import (
    PatchApprovalRepository,
)
from forgeai.infrastructure.models.patch_approval import PatchApprovalModel


class SQLAlchemyPatchApprovalRepository(PatchApprovalRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, approval: PatchApproval) -> PatchApproval:
        model = PatchApprovalModel(
            id=UUID(approval.approval_id),
            task_id=UUID(approval.task_id),
            agent_run_id=(UUID(approval.agent_run_id) if approval.agent_run_id else None),
            patch_sha256=approval.patch_sha256,
            status=approval.status.value,
            approved_by=approval.approved_by,
            decided_at=approval.decided_at,
            consumed_at=approval.consumed_at,
        )

        self.session.add(model)
        self.session.flush()

        return self._to_domain(model)

    def get_by_id(self, approval_id: UUID) -> PatchApproval | None:
        model = self.session.scalar(
            select(PatchApprovalModel).where(PatchApprovalModel.id == approval_id)
        )

        return self._to_domain(model) if model else None

    def get_by_id_for_update(
        self,
        approval_id: UUID,
    ) -> PatchApproval | None:
        model = self.session.scalar(
            select(PatchApprovalModel).where(PatchApprovalModel.id == approval_id).with_for_update()
        )

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
        model.consumed_at = approval.consumed_at

        self.session.flush()

        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: PatchApprovalModel) -> PatchApproval:
        return PatchApproval(
            approval_id=str(model.id),
            task_id=str(model.task_id),
            agent_run_id=(str(model.agent_run_id) if model.agent_run_id else None),
            patch_sha256=model.patch_sha256,
            status=ApprovalStatus(model.status),
            approved_by=(str(model.approved_by) if model.approved_by else None),
            decided_at=model.decided_at,
            consumed_at=model.consumed_at,
        )

    def get_by_run_and_patch(
        self,
        agent_run_id: UUID,
        patch_sha256: str,
    ) -> PatchApproval | None:
        """Find an approval for a specific run and patch fingerprint."""

        model = self.session.scalar(
            select(PatchApprovalModel).where(
                PatchApprovalModel.agent_run_id == agent_run_id,
                PatchApprovalModel.patch_sha256 == patch_sha256,
            )
        )

        return self._to_domain(model) if model else None
