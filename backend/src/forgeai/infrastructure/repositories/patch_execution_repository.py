
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.patch_execution import (
    PatchExecution,
    PatchExecutionStatus,
)
from forgeai.domain.repositories.patch_execution_repository import (
    PatchExecutionRepository,
)
from forgeai.infrastructure.models.patch_execution import (
    PatchExecutionModel,
)


class SQLAlchemyPatchExecutionRepository(PatchExecutionRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        execution: PatchExecution,
    ) -> PatchExecution:
        model = PatchExecutionModel(
            id=UUID(execution.execution_id),
            approval_id=UUID(execution.approval_id),
            task_id=UUID(execution.task_id),
            agent_run_id=UUID(execution.agent_run_id),
            patch_sha256=execution.patch_sha256,
            status=execution.status.value,
            sandbox_id=execution.sandbox_id,
            claimed_by=execution.claimed_by,
            claim_token=execution.claim_token,
            lease_expires_at=execution.lease_expires_at,
            claimed_at=execution.claimed_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error=execution.error,
        )

        self.session.add(model)
        self.session.flush()

        return self._to_domain(model)

    def get_by_id(
        self,
        execution_id: UUID,
    ) -> PatchExecution | None:
        statement = select(PatchExecutionModel).where(
            PatchExecutionModel.id == execution_id
        )

        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def get_by_approval_id(
        self,
        approval_id: UUID,
    ) -> PatchExecution | None:
        statement = select(PatchExecutionModel).where(
            PatchExecutionModel.approval_id == approval_id
        )

        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def get_by_id_for_update(
        self,
        execution_id: UUID,
    ) -> PatchExecution | None:
        statement = (
            select(PatchExecutionModel)
            .where(PatchExecutionModel.id == execution_id)
            .with_for_update()
        )

        model = self.session.scalar(statement)

        return self._to_domain(model) if model else None

    def update(
        self,
        execution: PatchExecution,
    ) -> PatchExecution:
        model = self.session.get(
            PatchExecutionModel,
            UUID(execution.execution_id),
        )

        if model is None:
            raise ValueError("Patch execution does not exist.")

        model.status = execution.status.value
        model.sandbox_id = execution.sandbox_id
        model.claimed_by = execution.claimed_by
        model.claim_token = execution.claim_token
        model.lease_expires_at = execution.lease_expires_at
        model.claimed_at = execution.claimed_at
        model.started_at = execution.started_at
        model.completed_at = execution.completed_at
        model.error = execution.error

        self.session.flush()

        return self._to_domain(model)

    @staticmethod
    def _to_domain(
        model: PatchExecutionModel,
    ) -> PatchExecution:
        return PatchExecution(
            execution_id=str(model.id),
            approval_id=str(model.approval_id),
            task_id=str(model.task_id),
            agent_run_id=str(model.agent_run_id),
            patch_sha256=model.patch_sha256,
            status=PatchExecutionStatus(model.status),
            sandbox_id=model.sandbox_id,
            claimed_by=model.claimed_by,
            claim_token=model.claim_token,
            lease_expires_at=model.lease_expires_at,
            claimed_at=model.claimed_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error=model.error,
        )
