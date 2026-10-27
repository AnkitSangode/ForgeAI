from uuid import uuid4

from forgeai.domain.task import Task
from forgeai.infrastructure.repositories.task_repository import TaskRepository


class FakeSession:
    def __init__(self) -> None:
        self.added = None
        self.flushed = False
        self.result = None

    def add(self, instance) -> None:
        self.added = instance

    def flush(self) -> None:
        self.flushed = True

    def scalar(self, statement):
        return self.result


def test_create_adds_and_flushes_task():
    session = FakeSession()
    repository = TaskRepository(session)

    task = Task(
        title="Fix failing tests",
        description="Investigate and fix the failing test suite.",
        repository_url="https://github.com/example/repo",
    )

    result = repository.create(task)

    assert result is task
    assert session.added is task
    assert session.flushed is True


def test_get_by_id_returns_matching_task():
    session = FakeSession()
    task_id = uuid4()

    task = Task(
        id=task_id,
        title="Fix failing tests",
        description="Investigate the test failures.",
        repository_url="https://github.com/example/repo",
    )

    session.result = task
    repository = TaskRepository(session)

    result = repository.get_by_id(task_id)

    assert result is task
