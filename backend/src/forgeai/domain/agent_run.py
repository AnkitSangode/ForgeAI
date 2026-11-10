from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class AgentRun:
    id: str
    task_id: str
    thread_id: str
    status: AgentRunStatus
    created_at: datetime
    updated_at: datetime