from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    thread_id: str
    status: str
    created_at: datetime
    updated_at: datetime
