
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from forgeai.application.agent_run_service import (
    AgentRunNotFoundError,
    AgentRunService,
)
from forgeai.domain.agent_run import AgentRun, AgentRunStatus


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(
    mock_session: MagicMock,
    mock_repository: MagicMock,
) -> AgentRunService:
    return AgentRunService(
        session=mock_session,
        repository=mock_repository,
    )


@pytest.fixture
def sample_run() -> AgentRun:
    run_id = uuid4()
    now = datetime.now(UTC)

    return AgentRun(
        id=str(run_id),
        task_id=str(uuid4()),
        thread_id=str(run_id),
        status=AgentRunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


class TestCreateRun:

    def test_create_run_success(
        self,
        service: AgentRunService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        task_id = str(uuid4())

        run = service.create_run(task_id)

        assert run.task_id == task_id
        assert run.status == AgentRunStatus.PENDING
        assert run.id == run.thread_id

        mock_repository.create.assert_called_once_with(run)
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_create_run_failure_rolls_back(
        self,
        service: AgentRunService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.create.side_effect = RuntimeError(
            "Database insertion failed"
        )

        with pytest.raises(RuntimeError, match="Database insertion failed"):
            service.create_run(str(uuid4()))

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestGetRun:

    def test_get_run_success(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
        sample_run: AgentRun,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_run

        result = service.get_run(sample_run.id)

        assert result == sample_run
        mock_repository.get_by_id.assert_called_once_with(
            UUID(sample_run.id)
        )

    def test_get_run_not_found(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
    ) -> None:
        run_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(AgentRunNotFoundError):
            service.get_run(str(run_id))


class TestGetRunByThreadId:

    def test_get_run_by_thread_id_success(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
        sample_run: AgentRun,
    ) -> None:
        mock_repository.get_by_thread_id.return_value = sample_run

        result = service.get_run_by_thread_id(sample_run.thread_id)

        assert result == sample_run
        mock_repository.get_by_thread_id.assert_called_once_with(
            sample_run.thread_id
        )

    def test_get_run_by_thread_id_not_found(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
    ) -> None:
        thread_id = str(uuid4())
        mock_repository.get_by_thread_id.return_value = None

        result = service.get_run_by_thread_id(thread_id)

        assert result is None
        mock_repository.get_by_thread_id.assert_called_once_with(thread_id)


class TestUpdateStatus:

    def test_update_status_success(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
        mock_session: MagicMock,
        sample_run: AgentRun,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_run

        result = service.update_status(
            run_id=sample_run.id,
            status=AgentRunStatus.RUNNING,
        )

        assert result.id == sample_run.id
        assert result.status == AgentRunStatus.RUNNING
        assert result.updated_at >= sample_run.updated_at

        mock_repository.update.assert_called_once_with(result)
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_update_status_run_not_found(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        run_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(AgentRunNotFoundError):
            service.update_status(
                run_id=str(run_id),
                status=AgentRunStatus.RUNNING,
            )

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    def test_update_status_failure_rolls_back(
        self,
        service: AgentRunService,
        mock_repository: MagicMock,
        mock_session: MagicMock,
        sample_run: AgentRun,
    ) -> None:
        mock_repository.get_by_id.return_value = sample_run
        mock_repository.update.side_effect = RuntimeError(
            "Database update failed"
        )

        with pytest.raises(RuntimeError, match="Database update failed"):
            service.update_status(
                run_id=sample_run.id,
                status=AgentRunStatus.RUNNING,
            )

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
