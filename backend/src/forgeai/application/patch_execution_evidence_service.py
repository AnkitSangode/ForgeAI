
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from forgeai.domain.patch_recovery_evidence import PatchRecoveryEvidence
from forgeai.domain.patch_test_evidence import PatchTestEvidence
from forgeai.domain.repositories.patch_recovery_evidence_repository import (
    PatchRecoveryEvidenceRepository,
)
from forgeai.domain.repositories.patch_test_evidence_repository import (
    PatchTestEvidenceRepository,
)

MAX_OUTPUT_CHARS = 20_000


class PatchExecutionEvidenceService:
    """Persists immutable test and recovery evidence."""

    def __init__(
        self,
        *,
        session: Session,
        test_evidence_repository: PatchTestEvidenceRepository,
        recovery_evidence_repository: PatchRecoveryEvidenceRepository,
    ) -> None:
        self.session = session
        self.test_evidence_repository = test_evidence_repository
        self.recovery_evidence_repository = recovery_evidence_repository

    def record_test_result(
        self,
        *,
        execution_id: str,
        attempt_id: str,
        patch_sha256: str,
        sequence_number: int,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool,
        started_at: datetime,
        completed_at: datetime | None = None,
    ) -> PatchTestEvidence:
        if sequence_number < 1:
            raise ValueError("sequence_number must be positive")

        self._validate_sha256(patch_sha256)
        self._validate_aware(started_at, "started_at")

        completed = completed_at or datetime.now(UTC)
        self._validate_aware(completed, "completed_at")

        if completed < started_at:
            raise ValueError("completed_at cannot precede started_at")

        evidence = PatchTestEvidence(
            evidence_id=str(uuid4()),
            execution_id=execution_id,
            attempt_id=attempt_id,
            patch_sha256=patch_sha256,
            sequence_number=sequence_number,
            command=command,
            exit_code=exit_code,
            stdout=(stdout or "")[-MAX_OUTPUT_CHARS:],
            stderr=(stderr or "")[-MAX_OUTPUT_CHARS:],
            timed_out=timed_out,
            started_at=started_at,
            completed_at=completed,
        )

        try:
            saved = self.test_evidence_repository.create(evidence)
            # Commit each command independently so later failures do not
            # roll back already completed test evidence.
            self.session.commit()
            return saved
        except Exception:
            self.session.rollback()
            raise

    def record_recovery_assessment(
        self,
        *,
        execution_id: str,
        sandbox_id: str | None,
        patch_sha256: str,
        disposition: str,
        reason: str,
        observed_files: tuple[str, ...],
        worker_stopped: bool,
        inspected_at: datetime | None = None,
    ) -> PatchRecoveryEvidence:
        self._validate_sha256(patch_sha256)

        inspected = inspected_at or datetime.now(UTC)
        self._validate_aware(inspected, "inspected_at")

        evidence = PatchRecoveryEvidence(
            evidence_id=str(uuid4()),
            execution_id=execution_id,
            sandbox_id=sandbox_id,
            patch_sha256=patch_sha256,
            disposition=disposition,
            reason=reason,
            observed_files=tuple(sorted(set(observed_files))),
            worker_stopped=worker_stopped,
            inspected_at=inspected,
        )

        try:
            saved = self.recovery_evidence_repository.create(evidence)
            self.session.commit()
            return saved
        except Exception:
            self.session.rollback()
            raise

    def get_test_evidence(self, execution_id: str) -> list[PatchTestEvidence]:
        return self.test_evidence_repository.get_by_execution_id(
            UUID(execution_id)
        )

    def get_recovery_evidence(
        self,
        execution_id: str,
    ) -> list[PatchRecoveryEvidence]:
        return self.recovery_evidence_repository.get_by_execution_id(
            UUID(execution_id)
        )

    @staticmethod
    def _validate_sha256(value: str) -> None:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value.lower())
        ):
            raise ValueError("patch_sha256 must be a valid SHA-256 hex digest")

    @staticmethod
    def _validate_aware(value: datetime, field_name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
