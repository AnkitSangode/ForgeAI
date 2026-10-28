from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from forgeai.api.schemas.task import TaskCreate, TaskRead
from forgeai.application.task_service import TaskNotFoundError, TaskService
from forgeai.infrastructure.session import get_db

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate, db: Annotated[Session, Depends(get_db)]
) -> TaskRead:
    service = TaskService(db)

    task = service.create_task(
        title=payload.title,
        description=payload.description,
        repository_url=str(payload.repository_url),
    )

    return TaskRead.model_validate(task)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, db: Annotated[Session, Depends(get_db)]) -> TaskRead:
    service = TaskService(db)

    try:
        task = service.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return TaskRead.model_validate(task)
