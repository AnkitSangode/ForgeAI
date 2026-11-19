
from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4

from forgeai.application.sandbox_patch_reconciliation_service import (
    SandboxPatchReconciliationService,
    SandboxReconciliationDisposition,
)
from forgeai.domain.patch_execution import PatchExecution, PatchExecutionStatus
from forgeai.execution.sandbox.base import SandboxSession
from forgeai.execution.schemas import GitRepositoryState

PATCH = "diff --git a/src/app.py b/src/app.py\n"
PATCH_HASH = SandboxPatchReconciliationService._sha256(PATCH)


def make_execution():
    return PatchExecution(
        execution_id=str(uuid4()),
        approval_id=str(uuid4()),
        task_id=str(uuid4()),
        agent_run_id=str(uuid4()),
        patch_sha256=PATCH_HASH,
        status=PatchExecutionStatus.RUNNING,
        sandbox_id="sandbox-123",
        claimed_by="worker-1",
        claim_token="claim-token",
    )


def make_change():
    return Mock(
        file_path="src/app.py",
        change_type="modify",
    )


def make_snapshot(
    modified=(),
    untracked=(),
    deleted=(),
):
    hashes = tuple(
        (path, "a" * 64)
        for path in sorted(set(modified) | set(untracked))
    )
    return GitRepositoryState(
        modified_files=frozenset(modified),
        untracked_files=frozenset(untracked),
        deleted_files=frozenset(deleted),
        file_hashes=hashes,
    )


def make_service():
    provider = Mock()
    provider.create_file.return_value = Mock()
    provider.file_exists.return_value = True

    collector = Mock()
    builder = Mock()
    builder.build.return_value = PATCH

    service = SandboxPatchReconciliationService(
        sandbox_provider=provider,
        git_state_collector=collector,
        patch_builder=builder,
    )

    session = SandboxSession(
        sandbox_id="sandbox-123",
        _handle=object(),
    )

    return service, provider, collector, builder, session


def git_result(exit_code):
    return Mock(exit_code=exit_code, stdout="", stderr="")


def test_worker_not_confirmed_stopped_requires_manual_review():
    service, provider, collector, _, session = make_service()

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=False,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert result.worker_stopped is False
    provider.run_command.assert_not_called()
    collector.capture.assert_not_called()


def test_sandbox_id_mismatch_requires_manual_review():
    service, provider, collector, _, _ = make_service()
    session = SandboxSession("different-sandbox", object())

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert "does not match" in result.reason
    provider.run_command.assert_not_called()
    collector.capture.assert_not_called()


def test_missing_execution_sandbox_id_requires_manual_review():
    service, provider, collector, _, session = make_service()
    execution = replace(make_execution(), sandbox_id=None)

    result = service.reconcile(
        execution=execution,
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    provider.run_command.assert_not_called()
    collector.capture.assert_not_called()


def test_empty_changes_require_manual_review():
    service, provider, collector, _, session = make_service()

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    collector.capture.assert_not_called()


def test_duplicate_change_paths_require_manual_review():
    service, provider, collector, _, session = make_service()
    change = make_change()

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[change, change],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    collector.capture.assert_not_called()


def test_patch_fingerprint_mismatch_requires_manual_review():
    service, provider, collector, _, session = make_service()
    execution = replace(make_execution(), patch_sha256="b" * 64)

    result = service.reconcile(
        execution=execution,
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert "fingerprint" in result.reason
    provider.create_file.assert_not_called()
    collector.capture.assert_not_called()


def test_exact_patch_already_applied_returns_fully_applied():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot(modified={"src/app.py"})
    provider.run_command.return_value = git_result(0)

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.FULLY_APPLIED
    assert result.observed_files == ("src/app.py",)
    assert result.worker_stopped is True
    assert provider.run_command.call_count == 1


def test_clean_repository_and_forward_check_returns_not_applied():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot()
    provider.run_command.side_effect = [
        git_result(1),  # reverse check: not already applied
        git_result(0),  # forward check: can still apply
    ]

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.NOT_APPLIED
    assert result.observed_files == ()
    assert provider.run_command.call_count == 2


def test_partial_expected_changes_return_partially_applied():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot(modified={"src/app.py"})
    provider.run_command.side_effect = [
        git_result(1),
        git_result(1),
    ]

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.PARTIALLY_APPLIED


def test_unexpected_repository_changes_require_manual_review():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot(
        modified={"src/app.py", "src/other.py"}
    )
    provider.run_command.return_value = git_result(0)

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert "file set" in result.reason


def test_unrelated_dirty_repository_requires_manual_review():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot(
        modified={"src/other.py"}
    )
    provider.run_command.side_effect = [
        git_result(1),
        git_result(1),
    ]

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED


def test_git_change_type_mismatch_requires_manual_review():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot(
        untracked={"src/app.py"}
    )
    provider.run_command.return_value = git_result(0)

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],  # expected modify, observed untracked
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert "change types" in result.reason


def test_git_inspection_exception_requires_manual_review():
    service, provider, collector, _, session = make_service()
    collector.capture.side_effect = RuntimeError("sandbox unavailable")

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED
    assert "inspection failed" in result.reason



def test_temporary_patch_file_is_cleaned_up():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot()
    provider.run_command.side_effect = [
        git_result(1),
        git_result(0),
    ]

    service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    provider.create_file.assert_called_once()

    created_file_path = provider.create_file.call_args.args[1]

    provider.file_exists.assert_called_once_with(
        session,
        created_file_path,
    )

    provider.delete_file.assert_called_once_with(
        session,
        created_file_path,
    )



def test_cleanup_failure_does_not_change_assessment():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot()
    provider.run_command.side_effect = [
        git_result(1),
        git_result(0),
    ]
    provider.delete_file.side_effect = RuntimeError("cleanup failed")

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.NOT_APPLIED


def test_reconciliation_does_not_update_execution_repository():
    service, provider, collector, _, session = make_service()
    collector.capture.return_value = make_snapshot()
    provider.run_command.side_effect = [
        git_result(1),
        git_result(0),
    ]

    result = service.reconcile(
        execution=make_execution(),
        session=session,
        changes=[make_change()],
        worker_stopped=True,
    )

    assert result.disposition == SandboxReconciliationDisposition.NOT_APPLIED
    # This service has no execution repository dependency and cannot
    # transition execution status.
