from uuid import UUID

import pytest

from forgeai.application.task_service import TaskNotFoundError, TaskService


class FakeSession:
    def __init__(self, commit_error=None):
        self.commit_error = commit_error
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self):
        self.commit_calls += 1

        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self):
        self.rollback_calls += 1


class FakeTaskRepository:
    def __init__(self, task=None, create_error=None):
        self.task = task
        self.create_error = create_error
        self.created_task = None

    def create(self, task):
        if self.create_error is not None:
            raise self.create_error

        self.created_task = task
        return task

    def get_by_id(self, task_id: UUID):
        if self.task is not None and self.task.id == task_id:
            return self.task

        return None


def make_task_service(session, repository):
    service = TaskService(session)
    service.repository = repository
    return service


def test_create_task_commits_and_returns_task():
    session = FakeSession()
    repository = FakeTaskRepository()
    service = make_task_service(session, repository)

    result = service.create_task(
        title="Fix failing tests",
        description="Investigate and fix the test suite.",
        repository_url="https://github.com/example/repo",
    )

    assert result is repository.created_task
    assert result.title == "Fix failing tests"
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


def test_create_task_rolls_back_when_commit_fails():
    session = FakeSession(commit_error=RuntimeError("Simulated commit failure"))
    repository = FakeTaskRepository()
    service = make_task_service(session, repository)

    with pytest.raises(
        RuntimeError,
        match="Simulated commit failure",
    ):
        service.create_task(
            title="Fix failing tests",
            description="Investigate the failure.",
            repository_url="https://github.com/example/repo",
        )

    assert session.commit_calls == 1
    assert session.rollback_calls == 1


def test_create_task_rolls_back_when_repository_fails():
    session = FakeSession()
    repository = FakeTaskRepository(
        create_error=RuntimeError("Simulated repository failure")
    )
    service = make_task_service(session, repository)

    with pytest.raises(
        RuntimeError,
        match="Simulated repository failure",
    ):
        service.create_task(
            title="Fix failing tests",
            description="Investigate the failure.",
            repository_url="https://github.com/example/repo",
        )

    assert session.commit_calls == 0
    assert session.rollback_calls == 1


def test_get_task_raises_when_task_does_not_exist():
    session = FakeSession()
    repository = FakeTaskRepository()
    service = make_task_service(session, repository)

    task_id = UUID("12345678-1234-5678-1234-567812345678")

    with pytest.raises(
        TaskNotFoundError,
        match="was not found",
    ):
        service.get_task(task_id)
