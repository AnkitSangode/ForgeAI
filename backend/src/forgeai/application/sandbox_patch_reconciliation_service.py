
from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from forgeai.agent.coder_schema import CodeChange
from forgeai.domain.patch_execution import PatchExecution
from forgeai.execution.git_state_collector import GitStateCollector
from forgeai.execution.repository_paths import REPOSITORY_ROOT
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession

logger = logging.getLogger(__name__)


class SandboxReconciliationDisposition(str, Enum):
    NOT_APPLIED = "not_applied"
    FULLY_APPLIED = "fully_applied"
    PARTIALLY_APPLIED = "partially_applied"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


@dataclass(frozen=True)
class SandboxReconciliationResult:
    execution_id: str
    disposition: SandboxReconciliationDisposition
    reason: str
    observed_files: tuple[str, ...] = ()
    worker_stopped: bool = False


class SandboxPatchReconciliationService:
    """Read-only inspection of an interrupted patch execution.

    The service never reapplies patches or changes execution status.

    worker_stopped must come from an authoritative worker-liveness
    mechanism. An expired database lease alone is not sufficient.
    """

    COMMAND_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        *,
        sandbox_provider: SandboxProvider,
        git_state_collector: GitStateCollector,
        patch_builder,
    ) -> None:
        self.sandbox_provider = sandbox_provider
        self.git_state_collector = git_state_collector
        self.patch_builder = patch_builder

    def reconcile(
        self,
        *,
        execution: PatchExecution,
        session: SandboxSession,
        changes: list[CodeChange],
        worker_stopped: bool,
    ) -> SandboxReconciliationResult:
        execution_id = execution.execution_id

        if not worker_stopped:
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "The previous worker is not confirmed stopped.",
                worker_stopped=False,
            )

        if not execution.sandbox_id:
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Execution has no persisted sandbox ID.",
                worker_stopped=True,
            )

        if session.sandbox_id != execution.sandbox_id:
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Connected sandbox does not match the execution sandbox.",
                worker_stopped=True,
            )

        if not changes:
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "No approved changes were supplied for reconciliation.",
                worker_stopped=True,
            )

        expected_paths = [change.file_path for change in changes]

        if len(expected_paths) != len(set(expected_paths)):
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Approved changes contain duplicate paths.",
                worker_stopped=True,
            )

        patch = self.patch_builder.build(changes)
        patch_hash = self._sha256(patch)

        if patch_hash != execution.patch_sha256:
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Reconstructed patch does not match the persisted fingerprint.",
                worker_stopped=True,
            )

        # A unique file avoids overwriting a patch left by the old worker.
        patch_file = f".forgeai-recovery-{uuid4().hex}.patch"
        git_patch_path = f"../{patch_file}"

        try:
            self.sandbox_provider.create_file(
                session,
                patch_file,
                patch,
            )

            snapshot = self.git_state_collector.capture(session)

            observed_paths = (
                snapshot.modified_files
                | snapshot.untracked_files
                | snapshot.deleted_files
            )

            expected_path_set = set(expected_paths)

            # Check whether the exact approved patch is already applied.
            reverse_result = self._run_git_check(
                session,
                f"git -C {shlex.quote(REPOSITORY_ROOT)} "
                f"apply --reverse --check {shlex.quote(git_patch_path)}",
            )

            if reverse_result == 0:
                if observed_paths != expected_path_set:
                    return self._result(
                        execution_id,
                        SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                        "The patch appears applied, but repository changes do not "
                        "match the approved file set.",
                        observed_paths,
                        True,
                    )

                if not self._change_types_match(changes, snapshot):
                    return self._result(
                        execution_id,
                        SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                        "Git change types do not match the approved operations.",
                        observed_paths,
                        True,
                    )

                return self._result(
                    execution_id,
                    SandboxReconciliationDisposition.FULLY_APPLIED,
                    "The exact approved patch is present in the sandbox.",
                    observed_paths,
                    True,
                )

            # If reverse-check fails, check whether the patch can still
            # be applied to the current repository without modifying it.
            forward_result = self._run_git_check(
                session,
                f"git -C {shlex.quote(REPOSITORY_ROOT)} "
                f"apply --check {shlex.quote(git_patch_path)}",
            )

            if forward_result == 0 and not observed_paths:
                return self._result(
                    execution_id,
                    SandboxReconciliationDisposition.NOT_APPLIED,
                    "The repository is clean and the approved patch can still apply.",
                    observed_paths,
                    True,
                )

            if observed_paths & expected_path_set:
                return self._result(
                    execution_id,
                    SandboxReconciliationDisposition.PARTIALLY_APPLIED,
                    "Some expected repository changes exist, but the exact patch "
                    "cannot be verified as fully applied.",
                    observed_paths,
                    True,
                )

            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Git could not establish whether the approved patch was applied.",
                observed_paths,
                True,
            )

        except Exception:
            logger.exception(
                "Sandbox reconciliation failed for execution %s",
                execution_id,
            )
            return self._result(
                execution_id,
                SandboxReconciliationDisposition.MANUAL_REVIEW_REQUIRED,
                "Sandbox inspection failed; repository state is unknown.",
                worker_stopped=True,
            )

        finally:
            try:
                if self.sandbox_provider.file_exists(session, patch_file):
                    self.sandbox_provider.delete_file(session, patch_file)
            except Exception:
                logger.exception(
                    "Could not clean up reconciliation patch file for %s",
                    execution_id,
                )

    def _run_git_check(self, session: SandboxSession, command: str) -> int:
        result = self.sandbox_provider.run_command(
            session,
            command,
            self.COMMAND_TIMEOUT_SECONDS,
        )
        return result.exit_code

    @staticmethod
    def _change_types_match(changes, snapshot) -> bool:
        expected = {
            "create": "untracked",
            "modify": "modified",
            "delete": "deleted",
        }

        actual = {}

        for path in snapshot.modified_files:
            actual[path] = "modified"

        for path in snapshot.untracked_files:
            actual[path] = "untracked"

        for path in snapshot.deleted_files:
            actual[path] = "deleted"

        return all(
            actual.get(change.file_path) == expected.get(change.change_type)
            for change in changes
        )

    @staticmethod
    def _sha256(value: str) -> str:
        import hashlib
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _result(
        execution_id,
        disposition,
        reason,
        observed_files=(),
        worker_stopped=False,
    ):
        return SandboxReconciliationResult(
            execution_id=execution_id,
            disposition=disposition,
            reason=reason,
            observed_files=tuple(sorted(observed_files)),
            worker_stopped=worker_stopped,
        )
