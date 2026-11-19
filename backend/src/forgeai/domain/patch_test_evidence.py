
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PatchTestEvidence:
    evidence_id: str
    execution_id: str
    attempt_id: str
    patch_sha256: str
    sequence_number: int
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    started_at: datetime
    completed_at: datetime
