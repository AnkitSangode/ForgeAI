from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PatchApproval:
    approval_id: str
    task_id: str
    agent_run_id: str | None
    patch_sha256: str
    status: ApprovalStatus
    approved_by: str | None
    decided_at: datetime | None
    consumed_at: datetime | None
