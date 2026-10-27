from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.domain.task import Task


class TaskRepository:
    """Encapsulates database operations for Task records"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, task: Task) -> Task:
        self.session.add(task)
        self.session.flush()
        return task

    def get_by_id(self, task_id: UUID) -> Task | None:
        statement = select(Task).where(Task.id == task_id)
        return self.session.scalar(statement)
