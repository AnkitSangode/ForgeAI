
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PatchExecutionStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class PatchExecution:
    execution_id: str
    approval_id: str
    task_id: str
    agent_run_id: str
    patch_sha256: str

    status: PatchExecutionStatus

    sandbox_id: str | None = None

    claimed_by: str | None = None
    claim_token: str | None = None
    lease_expires_at: datetime | None = None

    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    error: str | None = None
