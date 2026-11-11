from unittest.mock import Mock

import pytest

from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.git_state_collector import GitStateCollector
from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxFileResult,
    SandboxSession,
)


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
def collector(sandbox_provider):
    return GitStateCollector(sandbox_provider)


def make_git_result(stdout: str, exit_code: int = 0):
    return CommandExecutionResult(
        command=GitStateCollector.STATUS_COMMAND,
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
    )


def make_file_result(file_path: str, sha256: str):
    return SandboxFileResult(
        file_path=file_path,
        sha256=sha256,
    )


# ---------------------------------------------------------
# 1. Clean repository
# ---------------------------------------------------------


def test_capture_returns_empty_state_for_clean_repository(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result("")

    result = collector.capture(sandbox_session)

    assert result.modified_files == frozenset()
    assert result.untracked_files == frozenset()
    assert result.deleted_files == frozenset()
    assert result.file_hashes == ()

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


# ---------------------------------------------------------
# 2. Modified files
# ---------------------------------------------------------


def test_capture_records_modified_file_and_hash(
    collector,
    sandbox_provider,
    sandbox_session,
):
    file_hash = "a" * 64

    sandbox_provider.run_command.return_value = make_git_result(" M src/auth.py\x00")
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = make_file_result(
        "repository/src/auth.py",
        file_hash,
    )

    result = collector.capture(sandbox_session)

    assert result.modified_files == frozenset({"src/auth.py"})
    assert result.untracked_files == frozenset()
    assert result.deleted_files == frozenset()
    assert result.file_hashes == (("src/auth.py", file_hash),)

    sandbox_provider.file_exists.assert_called_once_with(
        sandbox_session,
        "repository/src/auth.py",
    )
    sandbox_provider.read_file.assert_called_once_with(
        sandbox_session,
        "repository/src/auth.py",
    )


def test_capture_handles_staged_modified_file(
    collector,
    sandbox_provider,
    sandbox_session,
):
    file_hash = "b" * 64

    sandbox_provider.run_command.return_value = make_git_result("M  src/auth.py\x00")
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = make_file_result(
        "repository/src/auth.py",
        file_hash,
    )

    result = collector.capture(sandbox_session)

    assert result.modified_files == frozenset({"src/auth.py"})
    assert result.file_hashes == (("src/auth.py", file_hash),)

    sandbox_provider.file_exists.assert_called_once_with(
        sandbox_session,
        "repository/src/auth.py",
    )


# ---------------------------------------------------------
# 3. Untracked files
# ---------------------------------------------------------


def test_capture_records_untracked_file_and_hash(
    collector,
    sandbox_provider,
    sandbox_session,
):
    file_hash = "c" * 64

    sandbox_provider.run_command.return_value = make_git_result("?? src/new_file.py\x00")
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = make_file_result(
        "repository/src/new_file.py",
        file_hash,
    )

    result = collector.capture(sandbox_session)

    assert result.untracked_files == frozenset({"src/new_file.py"})
    assert result.modified_files == frozenset()
    assert result.deleted_files == frozenset()
    assert result.file_hashes == (("src/new_file.py", file_hash),)

    sandbox_provider.file_exists.assert_called_once_with(
        sandbox_session,
        "repository/src/new_file.py",
    )
    sandbox_provider.read_file.assert_called_once_with(
        sandbox_session,
        "repository/src/new_file.py",
    )


# ---------------------------------------------------------
# 4. Deleted files
# ---------------------------------------------------------


def test_capture_records_deleted_file_without_hash(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(" D src/old_file.py\x00")

    result = collector.capture(sandbox_session)

    assert result.deleted_files == frozenset({"src/old_file.py"})
    assert result.modified_files == frozenset()
    assert result.untracked_files == frozenset()
    assert result.file_hashes == ()

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


def test_capture_handles_staged_deleted_file(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result("D  src/old_file.py\x00")

    result = collector.capture(sandbox_session)

    assert result.deleted_files == frozenset({"src/old_file.py"})
    assert result.file_hashes == ()


# ---------------------------------------------------------
# 5. Multiple files
# ---------------------------------------------------------


def test_capture_handles_multiple_file_changes(
    collector,
    sandbox_provider,
    sandbox_session,
):
    modified_hash = "d" * 64
    untracked_hash = "e" * 64

    sandbox_provider.run_command.return_value = make_git_result(
        " M src/auth.py\x00?? tests/test_auth.py\x00 D src/legacy.py\x00"
    )

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.side_effect = [
        make_file_result("repository/src/auth.py", modified_hash),
        make_file_result("repository/tests/test_auth.py", untracked_hash),
    ]

    result = collector.capture(sandbox_session)

    assert result.modified_files == frozenset({"src/auth.py"})
    assert result.untracked_files == frozenset({"tests/test_auth.py"})
    assert result.deleted_files == frozenset({"src/legacy.py"})

    # Hashes retain repository-relative paths and sorted order.
    assert result.file_hashes == (
        ("src/auth.py", modified_hash),
        ("tests/test_auth.py", untracked_hash),
    )

    assert [call.args[1] for call in sandbox_provider.file_exists.call_args_list] == [
        "repository/src/auth.py",
        "repository/tests/test_auth.py",
    ]

    assert [call.args[1] for call in sandbox_provider.read_file.call_args_list] == [
        "repository/src/auth.py",
        "repository/tests/test_auth.py",
    ]


# ---------------------------------------------------------
# 6. Git command failures
# ---------------------------------------------------------


def test_capture_raises_when_git_command_fails(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(
        "",
        exit_code=128,
    )

    with pytest.raises(
        PatchApplicationError,
        match="Unable to inspect repository state",
    ):
        collector.capture(sandbox_session)

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


# ---------------------------------------------------------
# 7. Missing files and hashes
# ---------------------------------------------------------


def test_capture_raises_when_changed_file_is_missing(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(" M src/auth.py\x00")
    sandbox_provider.file_exists.return_value = False

    with pytest.raises(
        PatchApplicationError,
        match="changed repository file could not be found",
    ):
        collector.capture(sandbox_session)

    sandbox_provider.file_exists.assert_called_once_with(
        sandbox_session,
        "repository/src/auth.py",
    )
    sandbox_provider.read_file.assert_not_called()


def test_capture_raises_when_file_hash_is_missing(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(" M src/auth.py\x00")
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="repository/src/auth.py",
        content="some content",
        sha256=None,
    )

    with pytest.raises(
        PatchApplicationError,
        match="Unable to calculate",
    ):
        collector.capture(sandbox_session)

    sandbox_provider.read_file.assert_called_once_with(
        sandbox_session,
        "repository/src/auth.py",
    )


# ---------------------------------------------------------
# 8. Unsupported Git states
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "git_status",
    [
        "R  src/new_auth.py\x00src/auth.py\x00",
        " C src/copied.py\x00src/auth.py\x00",
        "UU src/auth.py\x00",
    ],
)
def test_capture_rejects_rename_copy_and_conflict(
    collector,
    sandbox_provider,
    sandbox_session,
    git_status,
):
    sandbox_provider.run_command.return_value = make_git_result(git_status)

    with pytest.raises(PatchApplicationError):
        collector.capture(sandbox_session)

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


# ---------------------------------------------------------
# 9. Invalid Git output
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "git_output",
    [
        "invalid-record\x00",
        " M \x00",
        " M ../outside.py\x00",
        " M /etc/passwd\x00",
        " M src\\auth.py\x00",
        " M src/./auth.py\x00",
        " M src//auth.py\x00",
    ],
)
def test_capture_rejects_invalid_or_unsafe_paths(
    collector,
    sandbox_provider,
    sandbox_session,
    git_output,
):
    sandbox_provider.run_command.return_value = make_git_result(git_output)

    with pytest.raises(PatchApplicationError):
        collector.capture(sandbox_session)

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


# ---------------------------------------------------------
# 10. Verify provider calls
# ---------------------------------------------------------


def test_capture_uses_expected_git_command(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result("")

    collector.capture(sandbox_session)

    sandbox_provider.run_command.assert_called_once_with(
        sandbox_session,
        "git -C repository status --porcelain=v1 -z --untracked-files=all",
        GitStateCollector.COMMAND_TIMEOUT_SECONDS,
    )


def test_capture_hashes_files_in_sorted_order(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(" M z_file.py\x00 M a_file.py\x00")
    sandbox_provider.file_exists.return_value = True

    sandbox_provider.read_file.side_effect = [
        make_file_result("repository/a_file.py", "a" * 64),
        make_file_result("repository/z_file.py", "z" * 64),
    ]

    result = collector.capture(sandbox_session)

    assert result.file_hashes == (
        ("a_file.py", "a" * 64),
        ("z_file.py", "z" * 64),
    )

    assert [call.args[1] for call in sandbox_provider.read_file.call_args_list] == [
        "repository/a_file.py",
        "repository/z_file.py",
    ]


# ---------------------------------------------------------
# 11. Repository path isolation
# ---------------------------------------------------------


def test_git_snapshot_never_contains_workspace_prefix(
    collector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_git_result(" M src/auth.py\x00")
    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = make_file_result(
        "repository/src/auth.py",
        "f" * 64,
    )

    result = collector.capture(sandbox_session)

    assert "src/auth.py" in result.modified_files
    assert all(not file_path.startswith("repository/") for file_path in result.modified_files)

    assert result.file_hashes == (("src/auth.py", "f" * 64),)
