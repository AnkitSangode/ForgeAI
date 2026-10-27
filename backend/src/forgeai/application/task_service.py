from uuid import UUID

from sqlalchemy.orm import Session

from forgeai.domain.task import Task
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

    def get_task(self, task_id: UUID) -> Task:
        task = self.repository.get_by_id(task_id)

        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} was not found")

        return task
