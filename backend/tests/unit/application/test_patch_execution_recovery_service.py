from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from forgeai.application.patch_execution_recovery_service import (
    PatchExecutionRecoveryService,
    RecoveryDisposition,
)
from forgeai.domain.patch_execution import PatchExecution, PatchExecutionStatus

NOW = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)


def execution(status=PatchExecutionStatus.RUNNING):
    return PatchExecution(
        execution_id=str(uuid4()), approval_id=str(uuid4()), task_id=str(uuid4()),
        agent_run_id=str(uuid4()), patch_sha256="a" * 64, status=status,
        claimed_by="worker-1", claim_token="token", claimed_at=NOW-timedelta(minutes=10),
        started_at=NOW-timedelta(minutes=9) if status == PatchExecutionStatus.RUNNING else None,
        lease_expires_at=NOW-timedelta(minutes=5), sandbox_id="sandbox-1",
    )


@pytest.mark.parametrize("status", [PatchExecutionStatus.CLAIMED, PatchExecutionStatus.RUNNING])
def test_expired_active_execution_requires_reconciliation(status):
    result = PatchExecutionRecoveryService.assess(execution(status), now=NOW)
    assert result.disposition == RecoveryDisposition.RECONCILIATION_REQUIRED
    assert result.requires_sandbox_inspection


@pytest.mark.parametrize("status", [PatchExecutionStatus.CLAIMED, PatchExecutionStatus.RUNNING])
def test_unexpired_active_execution_is_untouched(status):
    item = replace(execution(status), lease_expires_at=NOW+timedelta(minutes=5))
    result = PatchExecutionRecoveryService.assess(item, now=NOW)
    assert result.disposition == RecoveryDisposition.NO_ACTION


@pytest.mark.parametrize("status", [PatchExecutionStatus.SUCCEEDED, PatchExecutionStatus.FAILED])
def test_terminal_execution_needs_no_action(status):
    assert PatchExecutionRecoveryService.assess(execution(status), now=NOW).disposition == RecoveryDisposition.NO_ACTION


def test_pending_execution_needs_no_action():
    item = replace(execution(PatchExecutionStatus.PENDING), claimed_by=None, claim_token=None,
                   claimed_at=None, lease_expires_at=None, started_at=None)
    assert PatchExecutionRecoveryService.assess(item, now=NOW).disposition == RecoveryDisposition.NO_ACTION


def test_pending_with_claim_metadata_is_invalid():
    assert PatchExecutionRecoveryService.assess(execution(PatchExecutionStatus.PENDING), now=NOW).disposition == RecoveryDisposition.INVALID_STATE


def test_missing_claim_token_is_invalid():
    assert PatchExecutionRecoveryService.assess(replace(execution(), claim_token=None), now=NOW).disposition == RecoveryDisposition.INVALID_STATE


def test_missing_start_time_is_invalid():
    assert PatchExecutionRecoveryService.assess(replace(execution(), started_at=None), now=NOW).disposition == RecoveryDisposition.INVALID_STATE


def test_expiry_at_current_time_requires_reconciliation():
    assert PatchExecutionRecoveryService.assess(replace(execution(), lease_expires_at=NOW), now=NOW).disposition == RecoveryDisposition.RECONCILIATION_REQUIRED


def test_naive_now_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        PatchExecutionRecoveryService.assess(execution(), now=NOW.replace(tzinfo=None))


def test_expiry_before_claim_is_invalid():
    item = replace(execution(), lease_expires_at=NOW-timedelta(minutes=11))
    assert PatchExecutionRecoveryService.assess(item, now=NOW).disposition == RecoveryDisposition.INVALID_STATE


def test_claimed_with_start_time_is_invalid():
    item = replace(execution(PatchExecutionStatus.CLAIMED), started_at=NOW-timedelta(minutes=9))
    assert PatchExecutionRecoveryService.assess(item, now=NOW).disposition == RecoveryDisposition.INVALID_STATE


def test_assess_by_id_reads_repository_without_writes():
    item = execution()
    repo = Mock()
    repo.get_by_id.return_value = item
    result = PatchExecutionRecoveryService(repo).assess_by_id(item.execution_id, now=NOW)
    assert result.disposition == RecoveryDisposition.RECONCILIATION_REQUIRED
    repo.get_by_id.assert_called_once()
    repo.update.assert_not_called()


def test_missing_execution_raises_lookup_error():
    repo = Mock()
    repo.get_by_id.return_value = None
    with pytest.raises(LookupError):
        PatchExecutionRecoveryService(repo).assess_by_id(str(uuid4()), now=NOW)
