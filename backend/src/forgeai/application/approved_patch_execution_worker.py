
from __future__ import annotations

import hashlib
import logging
import re
import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


MAX_TEST_COMMANDS = 10
MAX_TEST_COMMAND_LENGTH = 500
MAX_TEST_TIMEOUT_SECONDS = 120
MAX_TOTAL_TEST_SECONDS = 300


_ALLOWED_PYTEST_FLAGS = {
    "-q",
    "-v",
    "-x",
    "--maxfail=1",
    "--disable-warnings",
    "--tb=short",
    "--strict-markers",
}


_TEST_PATH_PATTERN = re.compile(
    r"^tests/[A-Za-z0-9_./-]*(?:\.py)?$"
)


class ApprovedPatchExecutionError(RuntimeError):
    """Raised when an approved patch cannot be safely executed."""


@dataclass(frozen=True)
class TestCommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class ApprovedPatchExecutionResult:
    execution_id: str
    success: bool
    changed_files: list[str] = field(default_factory=list)
    tests: list[TestCommandResult] = field(default_factory=list)
    tests_skipped: bool = False
    message: str = ""


class ApprovedPatchExecutionWorker:
    """
    Executes an approved patch inside an existing E2B sandbox.

    PatchExecutionService is responsible for:
      - Claiming an execution.
      - Issuing the claim token.
      - Starting execution.
      - Completing execution.
      - Failing execution.

    This worker is responsible for:
      - Verifying patch fingerprints.
      - Reconnecting to the sandbox.
      - Applying the approved patch.
      - Validating and executing test commands.
      - Persisting test execution evidence.
      - Reporting the final execution result.

    Sandbox SDK objects are never stored in LangGraph state.
    """

    def __init__(
        self,
        *,
        execution_service: Any,
        sandbox_provider: Any,
        patch_application_service: Any,
        patch_builder: Any,
        repository_context_factory: Callable[[dict[str, Any]], Any],
        worker_id: str,
        evidence_service: Any | None = None,
        test_timeout_seconds: int = MAX_TEST_TIMEOUT_SECONDS,
        total_test_timeout_seconds: int = MAX_TOTAL_TEST_SECONDS,
        terminate_on_success: bool = False,
    ) -> None:

        if not worker_id or not worker_id.strip():
            raise ValueError("worker_id must not be empty")

        if not 1 <= test_timeout_seconds <= MAX_TEST_TIMEOUT_SECONDS:
            raise ValueError(
                f"test_timeout_seconds must be between 1 and "
                f"{MAX_TEST_TIMEOUT_SECONDS}"
            )

        if not 1 <= total_test_timeout_seconds <= MAX_TOTAL_TEST_SECONDS:
            raise ValueError(
                f"total_test_timeout_seconds must be between 1 and "
                f"{MAX_TOTAL_TEST_SECONDS}"
            )

        self.execution_service = execution_service
        self.sandbox_provider = sandbox_provider
        self.patch_application_service = patch_application_service
        self.patch_builder = patch_builder
        self.repository_context_factory = repository_context_factory

        self.evidence_service = evidence_service

        self.worker_id = worker_id
        self.test_timeout_seconds = test_timeout_seconds
        self.total_test_timeout_seconds = total_test_timeout_seconds
        self.terminate_on_success = terminate_on_success

    def execute(
        self,
        *,
        execution_id: str,
        sandbox_id: str,
        changes: Sequence[Any],
        allowed_paths: set[str],
        repository_context_data: dict[str, Any],
        expected_patch_sha256: str,
        tests_to_run: Sequence[str] | None = None,
    ) -> ApprovedPatchExecutionResult:
        """
        Execute one approved patch.

        The fingerprint is checked against:

          1. The fingerprint supplied by the approval workflow.
          2. The fingerprint persisted in the execution record.

        Only after both checks pass can the execution be claimed.
        """

        if not execution_id:
            raise ValueError("execution_id is required")

        if not sandbox_id:
            raise ValueError("sandbox_id is required")

        if not expected_patch_sha256:
            raise ValueError("expected_patch_sha256 is required")

        # Build the exact patch that will be applied.
        patch = self.patch_builder.build(changes)

        actual_fingerprint = self._sha256(patch)

        # Check 1: compare against the approval workflow fingerprint.
        if actual_fingerprint != expected_patch_sha256:
            raise ApprovedPatchExecutionError(
                "Patch fingerprint does not match the approved patch"
            )

        # Check 2: compare against the persisted execution fingerprint.
        execution = self.execution_service.get_execution(execution_id)

        if execution.patch_sha256 != actual_fingerprint:
            raise ApprovedPatchExecutionError(
                "Persisted execution fingerprint does not match "
                "the supplied patch"
            )

        # Validate all commands before claiming the execution.
        validated_commands = self._validate_test_commands(
            tests_to_run or []
        )

        # One attempt ID identifies all test commands in this worker run.
        attempt_id = str(uuid4())

        # Claim is the durable concurrency boundary.
        claim = self.execution_service.claim_execution(
            execution_id=execution_id,
            worker_id=self.worker_id,
        )

        claim_token = claim.claim_token

        session = None
        completion_started = False

        try:
            # Reconnect using the serializable sandbox ID.
            session = self.sandbox_provider.connect(sandbox_id)

            # Persist sandbox ID immediately so recovery can locate it
            # even if the worker crashes before completion.
            self.execution_service.start_execution(
                execution_id=execution_id,
                claim_token=claim_token,
                sandbox_id=sandbox_id,
            )

            repository_context = self.repository_context_factory(
                repository_context_data
            )

            # Apply the patch. PatchApplicationService performs its own
            # path validation, integrity checks and Git verification.
            application_result = self.patch_application_service.apply(
                session=session,
                changes=changes,
                allowed_paths=allowed_paths,
                repository_context=repository_context,
            )

            if not application_result.success:
                raise ApprovedPatchExecutionError(
                    application_result.message
                    or "Patch application failed"
                )

            # Run validated tests after successful patch application.
            # Each completed command is persisted before the next command.
            test_results = self._run_tests(
                session=session,
                commands=validated_commands,
                execution_id=execution_id,
                attempt_id=attempt_id,
                patch_sha256=actual_fingerprint,
            )

            failed_tests = [
                result
                for result in test_results
                if result.exit_code != 0 or result.timed_out
            ]

            if failed_tests:
                details = "; ".join(
                    (
                        f"{result.command}: timed out"
                        if result.timed_out
                        else f"{result.command}: exit {result.exit_code}"
                    )
                    for result in failed_tests
                )

                raise ApprovedPatchExecutionError(
                    f"One or more tests failed: {details}"
                )

            # From this point, a database error may leave the final
            # transaction outcome uncertain. Do not blindly mark FAILED.
            completion_started = True

            self.execution_service.complete_execution(
                execution_id=execution_id,
                claim_token=claim_token,
                sandbox_id=sandbox_id,
            )

            # Cleanup happens only after success has been persisted.
            if self.terminate_on_success:
                self._terminate_safely(session)

            return ApprovedPatchExecutionResult(
                execution_id=execution_id,
                success=True,
                changed_files=list(
                    application_result.changed_files
                ),
                tests=test_results,
                tests_skipped=not bool(validated_commands),
                message=(
                    "Patch applied and verified."
                    if validated_commands
                    else "Patch applied; no test commands were supplied."
                ),
            )

        except Exception as exc:

            # Do not attempt a second state transition if completion
            # persistence has already started. Reconciliation is required.
            if not completion_started:
                try:
                    self.execution_service.fail_execution(
                        execution_id=execution_id,
                        claim_token=claim_token,
                        error=str(exc)[:2000],
                    )

                except Exception:
                    logger.exception(
                        "Could not persist failure for execution %s",
                        execution_id,
                    )

            logger.exception(
                "Approved patch execution %s failed",
                execution_id,
            )

            raise

    def _run_tests(
        self,
        *,
        session: Any,
        commands: Sequence[str],
        execution_id: str | None = None,
        attempt_id: str | None = None,
        patch_sha256: str | None = None,
    ) -> list[TestCommandResult]:
        """
        Execute validated test commands and persist each result.

        Evidence is written immediately after each command finishes.
        If evidence persistence fails, execution fails rather than
        silently continuing without an audit record.
        """

        results: list[TestCommandResult] = []

        total_budget = self.total_test_timeout_seconds

        for command in commands:

            timeout = min(
                self.test_timeout_seconds,
                total_budget,
            )

            if timeout <= 0:
                raise ApprovedPatchExecutionError(
                    "Total test execution time budget was exceeded"
                )

            # The command has already been validated and reconstructed
            # from parsed tokens. No arbitrary shell syntax is accepted.
            shell_command = f"cd repository && {command}"

            started_at = datetime.now(UTC)

            result = self.sandbox_provider.run_command(
                session=session,
                command=shell_command,
                timeout_seconds=timeout,
            )

            completed_at = datetime.now(UTC)

            timed_out = bool(
                getattr(result, "timed_out", False)
            )

            test_result = TestCommandResult(
                command=command,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                timed_out=timed_out,
            )

            results.append(test_result)

            # Persist evidence before moving to the next command.
            if self.evidence_service is not None:

                if not all(
                    (
                        execution_id,
                        attempt_id,
                        patch_sha256,
                    )
                ):
                    raise ApprovedPatchExecutionError(
                        "Test evidence metadata is incomplete"
                    )

                self.evidence_service.record_test_result(
                    execution_id=execution_id,
                    attempt_id=attempt_id,
                    patch_sha256=patch_sha256,
                    sequence_number=len(results),
                    command=command,
                    exit_code=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    timed_out=timed_out,
                    started_at=started_at,
                    completed_at=completed_at,
                )

            # Conservatively charge the full configured timeout.
            total_budget -= timeout

            if result.exit_code != 0 or timed_out:
                break

        return results

    @classmethod
    def _validate_test_commands(
        cls,
        commands: Sequence[str],
    ) -> list[str]:

        if len(commands) > MAX_TEST_COMMANDS:
            raise ApprovedPatchExecutionError(
                f"At most {MAX_TEST_COMMANDS} test commands are allowed"
            )

        validated: list[str] = []

        for command in commands:

            if not isinstance(command, str) or not command.strip():
                raise ApprovedPatchExecutionError(
                    "Test commands must be non-empty strings"
                )

            command = command.strip()

            if len(command) > MAX_TEST_COMMAND_LENGTH:
                raise ApprovedPatchExecutionError(
                    "Test command exceeds the maximum allowed length"
                )

            # Reject shell syntax before parsing.
            forbidden = (
                ";",
                "&&",
                "||",
                "|",
                ">",
                "<",
                "`",
                "$",
                "\n",
                "\r",
            )

            if any(token in command for token in forbidden):
                raise ApprovedPatchExecutionError(
                    "Shell operators and expansions are not allowed "
                    "in test commands"
                )

            try:
                tokens = shlex.split(command, posix=True)

            except ValueError as exc:
                raise ApprovedPatchExecutionError(
                    "Invalid test command syntax"
                ) from exc

            if not tokens:
                raise ApprovedPatchExecutionError(
                    "Empty test command"
                )

            # Keep executable tokens separate from arguments.
            if tokens[:3] == ["uv", "run", "pytest"]:
                executable = ["uv", "run", "pytest"]
                args = tokens[3:]

            elif tokens[:3] == ["python", "-m", "pytest"]:
                executable = ["python", "-m", "pytest"]
                args = tokens[3:]

            elif tokens[0] == "pytest":
                executable = ["pytest"]
                args = tokens[1:]

            else:
                raise ApprovedPatchExecutionError(
                    "Only 'uv run pytest', 'python -m pytest', "
                    "or 'pytest' commands are permitted"
                )

            if not args:
                raise ApprovedPatchExecutionError(
                    "A test command must specify at least one tests/ path"
                )

            for arg in args:

                if arg in _ALLOWED_PYTEST_FLAGS:
                    continue

                if arg.startswith("-"):
                    raise ApprovedPatchExecutionError(
                        f"Pytest option is not allowed: {arg}"
                    )

                normalized = arg.replace("\\", "/")

                if (
                    not _TEST_PATH_PATTERN.fullmatch(normalized)
                    or ".." in normalized.split("/")
                ):
                    raise ApprovedPatchExecutionError(
                        f"Test path is not allowed: {arg}"
                    )

            # Reconstruct without duplicating the pytest path.
            validated.append(
                shlex.join([*executable, *args])
            )

        return validated

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()

    def _terminate_safely(self, session: Any) -> None:

        try:
            self.sandbox_provider.terminate(session)

        except Exception:
            # The execution is already successful in the database.
            # A cleanup error must not reverse that result.
            logger.exception(
                "Execution succeeded but sandbox termination failed"
            )
