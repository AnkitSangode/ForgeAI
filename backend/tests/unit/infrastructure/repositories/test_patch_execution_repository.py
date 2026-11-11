
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from forgeai.domain.patch_execution import (
    PatchExecution,
    PatchExecutionStatus,
)
from forgeai.infrastructure.repositories.patch_execution_repository import (
    SQLAlchemyPatchExecutionRepository,
)


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository(session):
    return SQLAlchemyPatchExecutionRepository(session)


@pytest.fixture
def execution():
    now = datetime.now(UTC)

    return PatchExecution(
        execution_id=str(uuid4()),
        approval_id=str(uuid4()),
        task_id=str(uuid4()),
        agent_run_id=str(uuid4()),
        patch_sha256="a" * 64,
        status=PatchExecutionStatus.PENDING,
        sandbox_id=None,
        claimed_by=None,
        claim_token=None,
        lease_expires_at=None,
        claimed_at=None,
        started_at=None,
        completed_at=None,
        error=None,
    )


class TestCreate:

    def test_create_execution(self, repository, session, execution):
        result = repository.create(execution)

        session.add.assert_called_once()
        session.flush.assert_called_once()

        assert result.execution_id == execution.execution_id
        assert result.approval_id == execution.approval_id
        assert result.task_id == execution.task_id
        assert result.agent_run_id == execution.agent_run_id
        assert result.patch_sha256 == execution.patch_sha256
        assert result.status == PatchExecutionStatus.PENDING


class TestGetById:

    def test_get_execution_by_id(
        self,
        repository,
        session,
        execution,
    ):
        model = MagicMock()

        model.id = execution.execution_id
        model.approval_id = execution.approval_id
        model.task_id = execution.task_id
        model.agent_run_id = execution.agent_run_id
        model.patch_sha256 = execution.patch_sha256
        model.status = execution.status.value
        model.sandbox_id = None
        model.claimed_by = None
        model.claim_token = None
        model.lease_expires_at = None
        model.claimed_at = None
        model.started_at = None
        model.completed_at = None
        model.error = None

        session.scalar.return_value = model

        result = repository.get_by_id(
            __import__("uuid").UUID(execution.execution_id)
        )

        assert result.execution_id == execution.execution_id
        assert result.status == PatchExecutionStatus.PENDING

    def test_get_execution_by_id_not_found(
        self,
        repository,
        session,
    ):
        session.scalar.return_value = None

        result = repository.get_by_id(uuid4())

        assert result is None


class TestGetByApprovalId:

    def test_get_execution_by_approval_id(
        self,
        repository,
        session,
        execution,
    ):
        model = MagicMock()

        model.id = execution.execution_id
        model.approval_id = execution.approval_id
        model.task_id = execution.task_id
        model.agent_run_id = execution.agent_run_id
        model.patch_sha256 = execution.patch_sha256
        model.status = execution.status.value
        model.sandbox_id = None
        model.claimed_by = None
        model.claim_token = None
        model.lease_expires_at = None
        model.claimed_at = None
        model.started_at = None
        model.completed_at = None
        model.error = None

        session.scalar.return_value = model

        result = repository.get_by_approval_id(
            __import__("uuid").UUID(execution.approval_id)
        )

        assert result.approval_id == execution.approval_id

    def test_get_execution_by_approval_id_not_found(
        self,
        repository,
        session,
    ):
        session.scalar.return_value = None

        result = repository.get_by_approval_id(uuid4())

        assert result is None


class TestGetByIdForUpdate:

    def test_get_execution_for_update(
        self,
        repository,
        session,
        execution,
    ):
        model = MagicMock()

        model.id = execution.execution_id
        model.approval_id = execution.approval_id
        model.task_id = execution.task_id
        model.agent_run_id = execution.agent_run_id
        model.patch_sha256 = execution.patch_sha256
        model.status = execution.status.value
        model.sandbox_id = None
        model.claimed_by = None
        model.claim_token = None
        model.lease_expires_at = None
        model.claimed_at = None
        model.started_at = None
        model.completed_at = None
        model.error = None

        session.scalar.return_value = model

        result = repository.get_by_id_for_update(
            __import__("uuid").UUID(execution.execution_id)
        )

        assert result.execution_id == execution.execution_id
        session.scalar.assert_called_once()

    def test_get_execution_for_update_not_found(
        self,
        repository,
        session,
    ):
        session.scalar.return_value = None

        result = repository.get_by_id_for_update(uuid4())

        assert result is None


class TestUpdate:

    def test_update_execution(
        self,
        repository,
        session,
        execution,
    ):
        model = MagicMock()

        model.id = execution.execution_id
        model.approval_id = execution.approval_id
        model.task_id = execution.task_id
        model.agent_run_id = execution.agent_run_id
        model.patch_sha256 = execution.patch_sha256
        model.status = execution.status.value
        model.sandbox_id = None
        model.claimed_by = None
        model.claim_token = None
        model.lease_expires_at = None
        model.claimed_at = None
        model.started_at = None
        model.completed_at = None
        model.error = None

        session.get.return_value = model

        updated_execution = PatchExecution(
            execution_id=execution.execution_id,
            approval_id=execution.approval_id,
            task_id=execution.task_id,
            agent_run_id=execution.agent_run_id,
            patch_sha256=execution.patch_sha256,
            status=PatchExecutionStatus.RUNNING,
            sandbox_id="sandbox-123",
            claimed_by="worker-1",
            claim_token="claim-token-1",
            lease_expires_at=datetime.now(UTC),
            claimed_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )

        result = repository.update(updated_execution)

        assert model.status == "running"
        assert model.sandbox_id == "sandbox-123"
        assert model.claimed_by == "worker-1"
        assert model.claim_token == "claim-token-1"

        session.flush.assert_called_once()
        assert result.status == PatchExecutionStatus.RUNNING

    def test_update_execution_not_found(
        self,
        repository,
        session,
        execution,
    ):
        session.get.return_value = None

        with pytest.raises(ValueError, match="Patch execution does not exist"):
            repository.update(execution)

        session.flush.assert_not_called()
