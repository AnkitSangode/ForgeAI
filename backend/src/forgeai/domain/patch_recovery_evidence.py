
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PatchRecoveryEvidence:
    evidence_id: str
    execution_id: str
    sandbox_id: str | None
    patch_sha256: str
    disposition: str
    reason: str
    observed_files: tuple[str, ...]
    worker_stopped: bool
    inspected_at: datetime
