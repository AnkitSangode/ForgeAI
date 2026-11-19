
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from forgeai.application.patch_execution_evidence_service import (
    MAX_OUTPUT_CHARS,
    PatchExecutionEvidenceService,
)


def make_service():
    session = Mock()
    test_repository = Mock()
    recovery_repository = Mock()

    test_repository.create.side_effect = lambda item: item
    recovery_repository.create.side_effect = lambda item: item

    service = PatchExecutionEvidenceService(
        session=session,
        test_evidence_repository=test_repository,
        recovery_evidence_repository=recovery_repository,
    )

    return service, session, test_repository, recovery_repository


def test_test_evidence_is_persisted_and_committed():
    service, session, repository, _ = make_service()
    now = datetime.now(UTC)

    result = service.record_test_result(
        execution_id=str(uuid4()),
        attempt_id=str(uuid4()),
        patch_sha256="a" * 64,
        sequence_number=1,
        command="uv run pytest tests/unit -q",
        exit_code=0,
        stdout="passed",
        stderr="",
        timed_out=False,
        started_at=now,
    )

    repository.create.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()

    assert result.exit_code == 0
    assert result.stdout == "passed"


def test_test_evidence_limits_output_size():
    service, _, repository, _ = make_service()
    now = datetime.now(UTC)

    result = service.record_test_result(
        execution_id=str(uuid4()),
        attempt_id=str(uuid4()),
        patch_sha256="a" * 64,
        sequence_number=1,
        command="pytest tests/unit",
        exit_code=0,
        stdout="x" * (MAX_OUTPUT_CHARS + 100),
        stderr="y" * (MAX_OUTPUT_CHARS + 100),
        timed_out=False,
        started_at=now,
    )

    assert len(result.stdout) == MAX_OUTPUT_CHARS
    assert len(result.stderr) == MAX_OUTPUT_CHARS


def test_test_evidence_rolls_back_when_persistence_fails():
    service, session, repository, _ = make_service()
    repository.create.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError):
        service.record_test_result(
            execution_id=str(uuid4()),
            attempt_id=str(uuid4()),
            patch_sha256="a" * 64,
            sequence_number=1,
            command="pytest tests/unit",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            started_at=datetime.now(UTC),
        )

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_test_evidence_rejects_invalid_fingerprint():
    service, session, repository, _ = make_service()

    with pytest.raises(ValueError, match="SHA-256"):
        service.record_test_result(
            execution_id=str(uuid4()),
            attempt_id=str(uuid4()),
            patch_sha256="invalid",
            sequence_number=1,
            command="pytest tests/unit",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            started_at=datetime.now(UTC),
        )

    repository.create.assert_not_called()
    session.commit.assert_not_called()


def test_test_evidence_rejects_naive_timestamp():
    service, _, repository, _ = make_service()

    with pytest.raises(ValueError, match="timezone-aware"):
        service.record_test_result(
            execution_id=str(uuid4()),
            attempt_id=str(uuid4()),
            patch_sha256="a" * 64,
            sequence_number=1,
            command="pytest tests/unit",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            started_at=datetime.now(),
        )

    repository.create.assert_not_called()


def test_test_evidence_rejects_completion_before_start():
    service, _, repository, _ = make_service()
    now = datetime.now(UTC)

    with pytest.raises(ValueError, match="cannot precede"):
        service.record_test_result(
            execution_id=str(uuid4()),
            attempt_id=str(uuid4()),
            patch_sha256="a" * 64,
            sequence_number=1,
            command="pytest tests/unit",
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            started_at=now,
            completed_at=now - timedelta(seconds=1),
        )

    repository.create.assert_not_called()


def test_recovery_assessment_is_persisted():
    service, session, _, repository = make_service()

    result = service.record_recovery_assessment(
        execution_id=str(uuid4()),
        sandbox_id="sandbox-123",
        patch_sha256="b" * 64,
        disposition="manual_review_required",
        reason="Worker liveness is unknown.",
        observed_files=("src/app.py",),
        worker_stopped=False,
    )

    repository.create.assert_called_once()
    session.commit.assert_called_once()
    assert result.disposition == "manual_review_required"
    assert result.observed_files == ("src/app.py",)


def test_recovery_evidence_failure_rolls_back():
    service, session, _, repository = make_service()
    repository.create.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError):
        service.record_recovery_assessment(
            execution_id=str(uuid4()),
            sandbox_id="sandbox-123",
            patch_sha256="b" * 64,
            disposition="manual_review_required",
            reason="Inspection failed.",
            observed_files=(),
            worker_stopped=False,
        )

    session.rollback.assert_called_once()
    session.commit.assert_not_called()
