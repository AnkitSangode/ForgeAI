
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from unittest.mock import MagicMock

from forgeai.application.agent_run_service import (
    AgentRunNotFoundError,
    AgentRunService,
    InvalidAgentRunTransitionError,
)
from forgeai.domain.agent_run import AgentRun, AgentRunStatus


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repository():
    return MagicMock()


@pytest.fixture
def service(session, repository):
    return AgentRunService(
        session=session,
        repository=repository,
    )


@pytest.fixture
def existing_run():
    now = datetime.now(UTC)

    return AgentRun(
        id=str(uuid4()),
        task_id=str(uuid4()),
        thread_id=str(uuid4()),
        status=AgentRunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


class TestCreateRun:

    def test_create_run_success(self, service, repository, session):
        task_id = str(uuid4())

        result = service.create_run(task_id)

        assert result.task_id == task_id
        assert result.status == AgentRunStatus.PENDING
        assert result.id == result.thread_id

        repository.create.assert_called_once()
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    def test_create_run_rolls_back_on_error(
        self,
        service,
        repository,
        session,
    ):
        repository.create.side_effect = RuntimeError("Database error")

        with pytest.raises(RuntimeError):
            service.create_run(str(uuid4()))

        session.rollback.assert_called_once()
        session.commit.assert_not_called()


class TestGetRun:

    def test_get_run_success(
        self,
        service,
        repository,
        existing_run,
    ):
        repository.get_by_id.return_value = existing_run

        result = service.get_run(existing_run.id)

        assert result == existing_run
        repository.get_by_id.assert_called_once()

    def test_get_run_not_found(self, service, repository):
        repository.get_by_id.return_value = None

        with pytest.raises(AgentRunNotFoundError):
            service.get_run(str(uuid4()))


class TestUpdateStatus:

    @pytest.mark.parametrize(
        ("current_status", "next_status"),
        [
            (AgentRunStatus.PENDING, AgentRunStatus.RUNNING),
            (AgentRunStatus.PENDING, AgentRunStatus.FAILED),
            (AgentRunStatus.RUNNING, AgentRunStatus.AWAITING_APPROVAL),
            (AgentRunStatus.RUNNING, AgentRunStatus.REJECTED),
            (AgentRunStatus.RUNNING, AgentRunStatus.FAILED),
            (AgentRunStatus.AWAITING_APPROVAL, AgentRunStatus.EXECUTING),
            (AgentRunStatus.AWAITING_APPROVAL, AgentRunStatus.REJECTED),
            (AgentRunStatus.AWAITING_APPROVAL, AgentRunStatus.FAILED),
            (AgentRunStatus.EXECUTING, AgentRunStatus.SUCCEEDED),
            (AgentRunStatus.EXECUTING, AgentRunStatus.FAILED),
        ],
    )
    def test_valid_status_transition(
        self,
        service,
        repository,
        session,
        existing_run,
        current_status,
        next_status,
    ):
        run = replace(existing_run, status=current_status)
        repository.get_by_id.return_value = run

        result = service.update_status(
            run.id,
            next_status,
        )

        assert result.status == next_status
        assert result.updated_at >= run.updated_at

        repository.update.assert_called_once()
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(
        ("current_status", "next_status"),
        [
            (AgentRunStatus.PENDING, AgentRunStatus.AWAITING_APPROVAL),
            (AgentRunStatus.PENDING, AgentRunStatus.EXECUTING),
            (AgentRunStatus.PENDING, AgentRunStatus.SUCCEEDED),
            (AgentRunStatus.RUNNING, AgentRunStatus.EXECUTING),
            (AgentRunStatus.RUNNING, AgentRunStatus.SUCCEEDED),
            (AgentRunStatus.AWAITING_APPROVAL, AgentRunStatus.RUNNING),
            (AgentRunStatus.AWAITING_APPROVAL, AgentRunStatus.SUCCEEDED),
            (AgentRunStatus.EXECUTING, AgentRunStatus.RUNNING),
            (AgentRunStatus.SUCCEEDED, AgentRunStatus.RUNNING),
            (AgentRunStatus.REJECTED, AgentRunStatus.EXECUTING),
            (AgentRunStatus.FAILED, AgentRunStatus.RUNNING),
        ],
    )
    def test_invalid_status_transition(
        self,
        service,
        repository,
        session,
        existing_run,
        current_status,
        next_status,
    ):
        run = replace(existing_run, status=current_status)
        repository.get_by_id.return_value = run

        with pytest.raises(InvalidAgentRunTransitionError):
            service.update_status(
                run.id,
                next_status,
            )

        repository.update.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_called_once()

    @pytest.mark.parametrize(
        "terminal_status",
        [
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.REJECTED,
            AgentRunStatus.FAILED,
        ],
    )
    def test_terminal_status_cannot_transition(
        self,
        service,
        repository,
        existing_run,
        terminal_status,
    ):
        run = replace(existing_run, status=terminal_status)
        repository.get_by_id.return_value = run

        with pytest.raises(InvalidAgentRunTransitionError):
            service.update_status(
                run.id,
                AgentRunStatus.RUNNING,
            )

    def test_same_status_is_idempotent(
        self,
        service,
        repository,
        session,
        existing_run,
    ):
        run = replace(
            existing_run,
            status=AgentRunStatus.RUNNING,
        )
        repository.get_by_id.return_value = run

        result = service.update_status(
            run.id,
            AgentRunStatus.RUNNING,
        )

        assert result == run

        repository.update.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_not_called()

    def test_update_status_run_not_found(
        self,
        service,
        repository,
        session,
    ):
        repository.get_by_id.return_value = None

        with pytest.raises(AgentRunNotFoundError):
            service.update_status(
                str(uuid4()),
                AgentRunStatus.RUNNING,
            )

        repository.update.assert_not_called()
        session.commit.assert_not_called()
        session.rollback.assert_called_once()

    def test_update_status_rolls_back_on_repository_error(
        self,
        service,
        repository,
        session,
        existing_run,
    ):
        repository.get_by_id.return_value = existing_run
        repository.update.side_effect = RuntimeError("Database error")

        with pytest.raises(RuntimeError):
            service.update_status(
                existing_run.id,
                AgentRunStatus.RUNNING,
            )

        session.rollback.assert_called_once()
        session.commit.assert_not_called()
