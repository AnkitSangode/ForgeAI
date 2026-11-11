from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from forgeai.application.patch_approval_service import (
    PatchApprovalStateError,
)
from forgeai.application.patch_execution_service import (
    PatchExecutionNotFoundError,
    PatchExecutionService,
    PatchExecutionStateError,
)
from forgeai.domain.patch_approval import ApprovalStatus, PatchApproval
from forgeai.domain.patch_execution import (
    PatchExecution,
    PatchExecutionStatus,
)


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def execution_repository():
    repository = MagicMock()
    repository.get_by_approval_id.return_value = None
    repository.get_by_id.return_value = None

    return repository


@pytest.fixture
def approval_repository():
    return MagicMock()


@pytest.fixture
def approval_service(session, approval_repository):
    service = MagicMock()
    service.session = session
    service.approval_repository = approval_repository
    return service


@pytest.fixture
def service(session, execution_repository, approval_service):
    return PatchExecutionService(
        session=session,
        execution_repository=execution_repository,
        approval_service=approval_service,
    )


@pytest.fixture
def identifiers():
    return {
        "approval_id": str(uuid4()),
        "task_id": str(uuid4()),
        "agent_run_id": str(uuid4()),
        "patch_sha256": "a" * 64,
    }


@pytest.fixture
def approved_patch(identifiers):
    return PatchApproval(
        approval_id=identifiers["approval_id"],
        task_id=identifiers["task_id"],
        agent_run_id=identifiers["agent_run_id"],
        patch_sha256=identifiers["patch_sha256"],
        status=ApprovalStatus.APPROVED,
        approved_by="reviewer-123",
        decided_at=datetime.now(UTC),
        consumed_at=None,
    )


@pytest.fixture
def existing_execution(identifiers):
    return PatchExecution(
        execution_id=str(uuid4()),
        approval_id=identifiers["approval_id"],
        task_id=identifiers["task_id"],
        agent_run_id=identifiers["agent_run_id"],
        patch_sha256=identifiers["patch_sha256"],
        status=PatchExecutionStatus.PENDING,
    )


class TestCreateExecution:

    def test_create_execution_success(
        self,
        service,
        session,
        execution_repository,
        approval_repository,
        approval_service,
        identifiers,
        approved_patch,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch
        execution_repository.get_by_approval_id.return_value = None

        approval_service.consume_approval_in_transaction.return_value = approved_patch

        def create_execution_side_effect(execution):
            return execution

        execution_repository.create.side_effect = create_execution_side_effect

        result = service.create_execution(**identifiers)

        assert result.approval_id == identifiers["approval_id"]
        assert result.task_id == identifiers["task_id"]
        assert result.agent_run_id == identifiers["agent_run_id"]
        assert result.patch_sha256 == identifiers["patch_sha256"]
        assert result.status == PatchExecutionStatus.PENDING

        approval_service.consume_approval_in_transaction.assert_called_once_with(
            **identifiers
        )

        execution_repository.create.assert_called_once()
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    def test_create_execution_locks_approval_first(
        self,
        service,
        execution_repository,
        approval_repository,
        identifiers,
        approved_patch,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch
        execution_repository.get_by_approval_id.return_value = None
        execution_repository.create.side_effect = lambda execution: execution

        service.approval_service.consume_approval_in_transaction.return_value = (
            approved_patch
        )

        service.create_execution(**identifiers)

        approval_repository.get_by_id_for_update.assert_called_once()

        execution_repository.get_by_approval_id.assert_called_once()

    def test_create_execution_is_idempotent(
        self,
        service,
        session,
        execution_repository,
        approval_repository,
        identifiers,
        approved_patch,
        existing_execution,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch
        execution_repository.get_by_approval_id.return_value = existing_execution

        result = service.create_execution(**identifiers)

        assert result == existing_execution

        execution_repository.create.assert_not_called()
        service.approval_service.consume_approval_in_transaction.assert_not_called()

        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    def test_create_execution_rejects_task_mismatch(
        self,
        service,
        session,
        approval_repository,
        identifiers,
        approved_patch,
    ):
        wrong_task_approval = PatchApproval(
            approval_id=approved_patch.approval_id,
            task_id=str(uuid4()),
            agent_run_id=approved_patch.agent_run_id,
            patch_sha256=approved_patch.patch_sha256,
            status=ApprovalStatus.APPROVED,
            approved_by=approved_patch.approved_by,
            decided_at=approved_patch.decided_at,
            consumed_at=None,
        )

        approval_repository.get_by_id_for_update.return_value = wrong_task_approval

        with pytest.raises(PatchExecutionStateError):
            service.create_execution(**identifiers)

        service.execution_repository.create.assert_not_called()
        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    def test_create_execution_rejects_run_mismatch(
        self,
        service,
        session,
        approval_repository,
        identifiers,
        approved_patch,
    ):
        wrong_run_approval = PatchApproval(
            approval_id=approved_patch.approval_id,
            task_id=approved_patch.task_id,
            agent_run_id=str(uuid4()),
            patch_sha256=approved_patch.patch_sha256,
            status=ApprovalStatus.APPROVED,
            approved_by=approved_patch.approved_by,
            decided_at=approved_patch.decided_at,
            consumed_at=None,
        )

        approval_repository.get_by_id_for_update.return_value = wrong_run_approval

        with pytest.raises(PatchExecutionStateError):
            service.create_execution(**identifiers)

        service.execution_repository.create.assert_not_called()
        session.rollback.assert_called_once()

    def test_create_execution_rejects_fingerprint_mismatch(
        self,
        service,
        session,
        approval_repository,
        identifiers,
        approved_patch,
    ):
        wrong_fingerprint_approval = PatchApproval(
            approval_id=approved_patch.approval_id,
            task_id=approved_patch.task_id,
            agent_run_id=approved_patch.agent_run_id,
            patch_sha256="b" * 64,
            status=ApprovalStatus.APPROVED,
            approved_by=approved_patch.approved_by,
            decided_at=approved_patch.decided_at,
            consumed_at=None,
        )

        approval_repository.get_by_id_for_update.return_value = (
            wrong_fingerprint_approval
        )

        with pytest.raises(PatchExecutionStateError):
            service.create_execution(**identifiers)

        service.execution_repository.create.assert_not_called()
        session.rollback.assert_called_once()

    def test_create_execution_rejects_missing_approval(
        self,
        service,
        session,
        approval_repository,
        identifiers,
    ):
        approval_repository.get_by_id_for_update.return_value = None

        with pytest.raises(PatchExecutionStateError):
            service.create_execution(**identifiers)

        service.execution_repository.create.assert_not_called()
        session.rollback.assert_called_once()

    def test_create_execution_rejects_already_consumed_approval(
        self,
        service,
        session,
        approval_repository,
        execution_repository,
        approval_service,
        identifiers,
        approved_patch,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch

        # No execution record exists yet.
        execution_repository.get_by_approval_id.return_value = None

        # Approval consumption detects that it was already consumed.
        approval_service.consume_approval_in_transaction.side_effect = (
            PatchApprovalStateError("Approval already consumed.")
        )

        with pytest.raises(
            PatchApprovalStateError,
            match="Approval already consumed",
        ):
            service.create_execution(**identifiers)

        approval_service.consume_approval_in_transaction.assert_called_once()

        execution_repository.create.assert_not_called()

        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    def test_create_execution_rejects_already_consumed_approval(
        self,
        service,
        session,
        approval_repository,
        approval_service,
        execution_repository,
        identifiers,
        approved_patch,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch

        # No execution exists yet, so the service must attempt
        # to consume the approval before creating one.
        execution_repository.get_by_approval_id.return_value = None

        approval_service.consume_approval_in_transaction.side_effect = (
            PatchApprovalStateError("Approval already consumed.")
        )

        with pytest.raises(PatchApprovalStateError):
            service.create_execution(**identifiers)

        approval_service.consume_approval_in_transaction.assert_called_once()
        execution_repository.create.assert_not_called()
        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    def test_create_execution_rolls_back_when_repository_fails(
        self,
        service,
        session,
        execution_repository,
        approval_repository,
        approval_service,
        identifiers,
        approved_patch,
    ):
        approval_repository.get_by_id_for_update.return_value = approved_patch
        execution_repository.get_by_approval_id.return_value = None

        approval_service.consume_approval_in_transaction.return_value = approved_patch

        execution_repository.create.side_effect = RuntimeError(
            "Database insertion failed."
        )

        with pytest.raises(RuntimeError):
            service.create_execution(**identifiers)

        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    def test_create_execution_rolls_back_when_approval_missing(
        self,
        service,
        session,
        approval_repository,
        identifiers,
    ):
        approval_repository.get_by_id_for_update.return_value = None

        with pytest.raises(PatchExecutionStateError):
            service.create_execution(**identifiers)

        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    @pytest.mark.parametrize(
        "invalid_field",
        [
            "approval_id",
            "task_id",
            "agent_run_id",
        ],
    )
    def test_create_execution_rejects_invalid_uuid(
        self,
        service,
        session,
        identifiers,
        invalid_field,
    ):
        invalid_identifiers = identifiers.copy()
        invalid_identifiers[invalid_field] = "not-a-valid-uuid"

        with pytest.raises(ValueError):
            service.create_execution(**invalid_identifiers)

        session.rollback.assert_called_once()
        service.execution_repository.create.assert_not_called()


class TestGetExecution:

    def test_get_execution_success(
        self,
        service,
        execution_repository,
        existing_execution,
    ):
        execution_repository.get_by_id.return_value = existing_execution

        result = service.get_execution(existing_execution.execution_id)

        assert result == existing_execution

        execution_repository.get_by_id.assert_called_once()

    def test_get_execution_not_found(
        self,
        service,
        execution_repository,
    ):
        execution_repository.get_by_id.return_value = None

        with pytest.raises(PatchExecutionNotFoundError):
            service.get_execution(str(uuid4()))

    def test_get_execution_invalid_uuid(self, service):
        with pytest.raises(PatchExecutionNotFoundError):
            service.get_execution("invalid-uuid")
