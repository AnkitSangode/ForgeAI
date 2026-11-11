from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: UUID
    task_id: UUID
    patch_sha256: str
    status: str
    approved_by: str | None
    decided_at: datetime | None
    consumed_at: datetime | None
