from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TaskCreate(BaseModel):
    """Validate data submitted when creating a task."""

    title: str = Field(min_length=1,max_length=200)
    description: str = Field(min_length=1)
    repository_url: HttpUrl


class TaskRead(BaseModel):
    """Define the task representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    repository_url: str
    status: str
    created_at: datetime
    updated_at: datetime