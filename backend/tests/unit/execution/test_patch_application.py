
from unittest.mock import Mock

import pytest

from forgeai.execution.exceptions import (
    FileIntegrityError,
    PatchApplicationError,
    PatchValidationError,
)
from forgeai.execution.patch_application import PatchApplicationService
from forgeai.execution.repository_paths import REPOSITORY_ROOT
from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxSession,
)


@pytest.fixture
def git_state_collector():
    return Mock()


@pytest.fixture
def git_change_verifier():
    return Mock()


@pytest.fixture
def sandbox_session():
    return SandboxSession(
        sandbox_id="test-sandbox",
        _handle=Mock(),
    )


@pytest.fixture
def sandbox_provider():
    return Mock()


@pytest.fixture
def patch_validator():
    return Mock()


@pytest.fixture
def integrity_verifier():
    return Mock()


@pytest.fixture
def post_application_verifier():
    return Mock()


@pytest.fixture
def service(
    sandbox_provider,
    patch_validator,
    integrity_verifier,
    post_application_verifier,
    git_state_collector,
    git_change_verifier,
):
    return PatchApplicationService(
        sandbox_provider=sandbox_provider,
        patch_validator=patch_validator,
        integrity_verifier=integrity_verifier,
        post_application_verifier=post_application_verifier,
        git_state_collector=git_state_collector,
        git_change_verifier=git_change_verifier,
    )


@pytest.fixture
def changes():
    return [
        Mock(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff=(
                "--- a/src/auth.py\n"
                "+++ b/src/auth.py\n"
                "@@ -1,2 +1,2 @@\n"
                "-old_value = True\n"
                "+old_value = False\n"
            ),
        )
    ]


@pytest.fixture
def repository_context():
    return Mock()


@pytest.fixture
def allowed_paths():
    return {"src/auth.py"}


def make_command_result(
    command: str,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
):
    return CommandExecutionResult(
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


@pytest.fixture
def successful_git_commands():
    return [
        make_command_result(
            "git -C repository rev-parse --is-inside-work-tree",
            stdout="true\n",
        ),
        make_command_result(
            "git -C repository apply --check ../.forgeai-current.patch",
        ),
        make_command_result(
            "git -C repository apply ../.forgeai-current.patch",
        ),
    ]


# ---------------------------------------------------------
# Validation and integrity
# ---------------------------------------------------------


def test_empty_changes_are_rejected(
    service,
    patch_validator,
    sandbox_session,
    repository_context,
    allowed_paths,
):
    patch_validator.validate.side_effect = PatchValidationError(
        "At least one code change is required."
    )

    with pytest.raises(PatchValidationError):
        service.apply(
            session=sandbox_session,
            changes=[],
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    patch_validator.validate.assert_called_once()
    service.integrity_verifier.verify.assert_not_called()


def test_unauthorized_path_is_rejected(
    service,
    patch_validator,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    patch_validator.validate.side_effect = PatchValidationError(
        "Patch target is not authorized."
    )

    with pytest.raises(PatchValidationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    service.integrity_verifier.verify.assert_not_called()


def test_invalid_unified_diff_is_rejected(
    service,
    patch_validator,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    patch_validator.validate.side_effect = PatchValidationError(
        "Unified diff contains no hunks."
    )

    with pytest.raises(PatchValidationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    service.integrity_verifier.verify.assert_not_called()


def test_modified_original_file_is_rejected(
    service,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    service.integrity_verifier.verify.side_effect = FileIntegrityError(
        "File has changed since repository inspection."
    )

    with pytest.raises(FileIntegrityError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    service.patch_validator.validate.assert_called_once()
    service.integrity_verifier.verify.assert_called_once()


def test_missing_original_file_is_rejected(
    service,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    service.integrity_verifier.verify.side_effect = FileIntegrityError(
        "Original file no longer exists."
    )

    with pytest.raises(FileIntegrityError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )


# ---------------------------------------------------------
# Successful execution
# ---------------------------------------------------------


def test_valid_patch_passes_validation_and_integrity_checks(
    service,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
    successful_git_commands,
):
    sandbox_provider.run_command.side_effect = successful_git_commands
    sandbox_provider.file_exists.return_value = True

    result = service.apply(
        session=sandbox_session,
        changes=changes,
        allowed_paths=allowed_paths,
        repository_context=repository_context,
    )

    assert result.success is True
    assert result.changed_files == ["src/auth.py"]

    service.patch_validator.validate.assert_called_once()
    service.integrity_verifier.verify.assert_called_once()
    service.post_application_verifier.verify.assert_called_once()

    sandbox_provider.create_file.assert_called_once()
    sandbox_provider.delete_file.assert_called_once()


def test_apply_executes_complete_pipeline(
    service,
    sandbox_provider,
    patch_validator,
    integrity_verifier,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
    successful_git_commands,
):
    sandbox_provider.run_command.side_effect = successful_git_commands
    sandbox_provider.file_exists.return_value = True

    result = service.apply(
        session=sandbox_session,
        changes=changes,
        allowed_paths=allowed_paths,
        repository_context=repository_context,
    )

    assert result.success is True
    assert result.changed_files == ["src/auth.py"]

    patch_validator.validate.assert_called_once()
    integrity_verifier.verify.assert_called_once()
    sandbox_provider.create_file.assert_called_once()
    sandbox_provider.delete_file.assert_called_once()


# ---------------------------------------------------------
# Patch construction
# ---------------------------------------------------------


def test_build_patch_combines_multiple_file_diffs():
    changes = [
        Mock(
            file_path="src/auth.py",
            unified_diff=(
                "--- a/src/auth.py\n"
                "+++ b/src/auth.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
        ),
        Mock(
            file_path="src/database.py",
            unified_diff=(
                "--- a/src/database.py\n"
                "+++ b/src/database.py\n"
                "@@ -1 +1 @@\n"
                "-old_db\n"
                "+new_db\n"
            ),
        ),
    ]

    patch = PatchApplicationService._build_patch(changes)

    assert patch.count("--- a/") == 2
    assert patch.count("+++ b/") == 2
    assert "src/auth.py" in patch
    assert "src/database.py" in patch
    assert patch.endswith("\n")


def test_build_patch_rejects_empty_changes():
    with pytest.raises(PatchApplicationError):
        PatchApplicationService._build_patch([])


# ---------------------------------------------------------
# Git repository validation
# ---------------------------------------------------------


def test_ensure_git_repository_accepts_valid_repository(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository rev-parse --is-inside-work-tree",
        stdout="true\n",
    )

    service._ensure_git_repository(sandbox_session)

    sandbox_provider.run_command.assert_called_once_with(
        session=sandbox_session,
        command="git -C repository rev-parse --is-inside-work-tree",
        timeout_seconds=30,
    )


def test_ensure_git_repository_rejects_invalid_repository(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository rev-parse --is-inside-work-tree",
        exit_code=128,
        stderr="fatal: not a git repository",
    )

    with pytest.raises(PatchApplicationError):
        service._ensure_git_repository(sandbox_session)


def test_git_commands_target_cloned_repository(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "",
        stdout="true\n",
    )

    service._ensure_git_repository(sandbox_session)

    command = sandbox_provider.run_command.call_args.kwargs["command"]

    assert command == (
        f"git -C {REPOSITORY_ROOT} rev-parse --is-inside-work-tree"
    )


# ---------------------------------------------------------
# Patch file creation and cleanup
# ---------------------------------------------------------


def test_write_patch_creates_patch_file(
    service,
    sandbox_provider,
    sandbox_session,
):
    patch = "--- a/src/auth.py\n+++ b/src/auth.py\n"

    service._write_patch(sandbox_session, patch)

    sandbox_provider.create_file.assert_called_once_with(
        session=sandbox_session,
        file_path=service.PATCH_FILE_PATH,
        content=patch,
    )


def test_write_patch_rejects_existing_patch_file(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.create_file.side_effect = FileExistsError()

    with pytest.raises(PatchApplicationError):
        service._write_patch(
            sandbox_session,
            "--- a/src/auth.py\n+++ b/src/auth.py\n",
        )


# ---------------------------------------------------------
# Git patch validation
# ---------------------------------------------------------


def test_check_patch_succeeds(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository apply --check ../.forgeai-current.patch",
    )

    service._check_patch(sandbox_session)

    sandbox_provider.run_command.assert_called_once_with(
        session=sandbox_session,
        command=(
            "git -C repository "
            "apply --check ../.forgeai-current.patch"
        ),
        timeout_seconds=30,
    )


def test_check_patch_fails(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository apply --check ../.forgeai-current.patch",
        exit_code=1,
        stderr="error: patch does not apply",
    )

    with pytest.raises(
        PatchApplicationError,
        match="Patch validation by Git failed",
    ):
        service._check_patch(sandbox_session)

    sandbox_provider.run_command.assert_called_once()


# ---------------------------------------------------------
# Git patch application
# ---------------------------------------------------------


def test_apply_patch_succeeds(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository apply ../.forgeai-current.patch",
    )

    service._apply_patch(sandbox_session)

    sandbox_provider.run_command.assert_called_once_with(
        session=sandbox_session,
        command=(
            "git -C repository "
            "apply ../.forgeai-current.patch"
        ),
        timeout_seconds=30,
    )


def test_apply_patch_fails(
    service,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        "git -C repository apply ../.forgeai-current.patch",
        exit_code=1,
        stderr="error: patch failed",
    )

    with pytest.raises(
        PatchApplicationError,
        match="Git failed to apply the patch",
    ):
        service._apply_patch(sandbox_session)

    sandbox_provider.run_command.assert_called_once()


# ---------------------------------------------------------
# Pipeline failure handling
# ---------------------------------------------------------


def test_apply_stops_when_validation_fails(
    service,
    sandbox_provider,
    patch_validator,
    integrity_verifier,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    patch_validator.validate.side_effect = PatchValidationError(
        "Invalid patch."
    )

    with pytest.raises(PatchValidationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    integrity_verifier.verify.assert_not_called()
    sandbox_provider.run_command.assert_not_called()
    sandbox_provider.create_file.assert_not_called()


def test_apply_stops_when_integrity_verification_fails(
    service,
    sandbox_provider,
    integrity_verifier,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    integrity_verifier.verify.side_effect = FileIntegrityError(
        "Original file has changed."
    )

    with pytest.raises(FileIntegrityError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    sandbox_provider.run_command.assert_not_called()
    sandbox_provider.create_file.assert_not_called()


def test_apply_does_not_apply_patch_when_git_check_fails(
    service,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    sandbox_provider.run_command.side_effect = [
        make_command_result(
            "git -C repository rev-parse --is-inside-work-tree",
            stdout="true\n",
        ),
        make_command_result(
            "git -C repository apply --check ../.forgeai-current.patch",
            exit_code=1,
            stderr="Patch conflict.",
        ),
    ]

    sandbox_provider.file_exists.return_value = True

    with pytest.raises(PatchApplicationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    assert sandbox_provider.run_command.call_count == 2
    sandbox_provider.delete_file.assert_called_once()


def test_apply_cleans_up_patch_after_execution_failure(
    service,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
):
    sandbox_provider.run_command.side_effect = [
        make_command_result(
            "git -C repository rev-parse --is-inside-work-tree",
            stdout="true\n",
        ),
        make_command_result(
            "git -C repository apply --check ../.forgeai-current.patch",
        ),
        make_command_result(
            "git -C repository apply ../.forgeai-current.patch",
            exit_code=1,
            stderr="Application failed.",
        ),
    ]

    sandbox_provider.file_exists.return_value = True

    with pytest.raises(PatchApplicationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    sandbox_provider.delete_file.assert_called_once()


def test_apply_fails_when_post_application_verification_fails(
    service,
    sandbox_provider,
    post_application_verifier,
    sandbox_session,
    changes,
    repository_context,
):
    post_application_verifier.verify.side_effect = FileIntegrityError(
        "Post-application verification failed."
    )

    sandbox_provider.run_command.side_effect = [
        make_command_result(
            "git -C repository rev-parse --is-inside-work-tree",
            stdout="true\n",
        ),
        make_command_result(
            "git -C repository apply --check ../.forgeai-current.patch",
        ),
        make_command_result(
            "git -C repository apply ../.forgeai-current.patch",
        ),
    ]

    sandbox_provider.file_exists.return_value = True

    with pytest.raises(FileIntegrityError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths={"src/auth.py"},
            repository_context=repository_context,
        )

    post_application_verifier.verify.assert_called_once()

    sandbox_provider.delete_file.assert_called_once_with(
        sandbox_session,
        service.PATCH_FILE_PATH,
    )


# ---------------------------------------------------------
# Git state verification
# ---------------------------------------------------------


def test_apply_captures_baseline_and_final_git_state(
    service,
    git_state_collector,
    git_change_verifier,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
    successful_git_commands,
):
    sandbox_provider.run_command.side_effect = successful_git_commands
    sandbox_provider.file_exists.return_value = True

    service.apply(
        session=sandbox_session,
        changes=changes,
        allowed_paths=allowed_paths,
        repository_context=repository_context,
    )

    assert git_state_collector.capture.call_count == 2

    git_change_verifier.verify.assert_called_once_with(
        baseline=git_state_collector.capture.return_value,
        final_state=git_state_collector.capture.return_value,
        expected_changes=changes,
    )


def test_apply_fails_when_unexpected_repository_changes_are_detected(
    service,
    git_change_verifier,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
    successful_git_commands,
):
    sandbox_provider.run_command.side_effect = successful_git_commands
    sandbox_provider.file_exists.return_value = True

    git_change_verifier.verify.side_effect = PatchApplicationError(
        "Execution modified files outside the authorized patch."
    )

    with pytest.raises(PatchApplicationError):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )

    sandbox_provider.delete_file.assert_called_once_with(
        sandbox_session,
        service.PATCH_FILE_PATH,
    )


# ---------------------------------------------------------
# Cleanup failure handling
# ---------------------------------------------------------


def test_apply_does_not_report_success_when_patch_cleanup_fails(
    service,
    sandbox_provider,
    sandbox_session,
    changes,
    repository_context,
    allowed_paths,
    successful_git_commands,
):
    sandbox_provider.run_command.side_effect = successful_git_commands
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.delete_file.side_effect = PermissionError(
        "Permission denied"
    )

    with pytest.raises(
        PatchApplicationError,
        match="Failed to clean up",
    ):
        service.apply(
            session=sandbox_session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )
