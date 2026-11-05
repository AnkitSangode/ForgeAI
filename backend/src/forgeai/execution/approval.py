from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PatchApproval:
    """Represents a human decision for a specific patch."""

    approval_id: str
    task_id: str
    patch_sha256: str
    status: ApprovalStatus
    approved_by: str | None
    decided_at: datetime | None

    def __post_init__(self) -> None:
        if len(self.patch_sha256) != 64:
            raise ValueError("Patch fingerprint must be a SHA-256 hash.")

        try:
            int(self.patch_sha256, 16)
        except ValueError as exc:
            raise ValueError("Patch fingerprint must be hexadecimal.") from exc
