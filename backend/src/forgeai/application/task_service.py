from uuid import UUID

from sqlalchemy.orm import Session

from forgeai.infrastructure.models.task import Task
from forgeai.infrastructure.repositories.task_repository import TaskRepository


class TaskNotFoundError(Exception):
    """Requested task does not exist"""


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = TaskRepository(session)

    def create_task(self, title: str, description: str, repository_url: str) -> Task:
        task = Task(
            title=title,
            description=description,
            repository_url=repository_url,
        )

        try:
            self.repository.create(task)
            self.session.commit()
            return task
        except Exception:
            self.session.rollback()
            raise

    def list_tasks(self, *, offset: int = 0, limit: int = 50) -> list[Task]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return self.repository.list(offset=offset, limit=limit)

    def get_task(self, task_id: UUID) -> Task:
        task = self.repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found")

        return task
