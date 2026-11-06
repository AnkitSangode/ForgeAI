
from unittest.mock import Mock

import pytest

from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxSession,
)
from forgeai.services.repository_inspector import (
    IMPORTANT_FILES,
    MAX_REPOSITORY_FILES,
    SandboxRepositoryInspector,
)


@pytest.fixture
def sandbox_session():
    return SandboxSession(
        sandbox_id="test-sandbox-123",
        _handle=Mock(),
    )


@pytest.fixture
def sandbox_provider():
    return Mock()


@pytest.fixture
def inspector(sandbox_provider):
    return SandboxRepositoryInspector(
        sandbox_provider=sandbox_provider
    )


def make_command_result(stdout="", exit_code=0, stderr=""):
    return CommandExecutionResult(
        command="find repository",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_inspect_valid_repository(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=(
            "repository/README.md\x00"
            "repository/requirements.txt\x00"
        )
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "available"
    assert result.error is None
    assert set(result.files) == {
        "README.md",
        "requirements.txt",
    }

    sandbox_provider.run_command.assert_called_once()


def test_inspect_rejects_invalid_repository_path(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    result = inspector.inspect(
        sandbox_session,
        repository_path="../outside",
    )

    assert result.status == "unavailable"
    assert result.files == []
    assert (
        result.error
        == "Repository path must be the configured repository directory."
    )

    sandbox_provider.run_command.assert_not_called()


def test_inspect_handles_command_failure(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        exit_code=1,
        stderr="Repository directory does not exist.",
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "unavailable"
    assert result.files == []
    assert (
        result.error
        == "Repository inspection failed: "
        "Repository directory does not exist."
    )


def test_inspect_handles_sandbox_exception(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.side_effect = RuntimeError(
        "Sandbox connection failed."
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "unavailable"
    assert result.files == []
    assert (
        result.error
        == "Repository inspection failed: Sandbox connection failed."
    )


def test_inspect_excludes_unnecessary_directories(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    # The sandbox find command is responsible for excluding these
    # directories. Simulate its output after exclusions.
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=(
            "repository/src/main.py\x00"
        )
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "available"
    assert result.files == ["src/main.py"]

    command = sandbox_provider.run_command.call_args.kwargs["command"]

    for excluded_directory in (
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
    ):
        assert excluded_directory in command


def test_inspect_nested_directories(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=(
            "repository/src/services/auth.py\x00"
            "repository/src/services/user.py\x00"
        )
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "available"
    assert set(result.files) == {
        "src/services/auth.py",
        "src/services/user.py",
    }


def test_inspect_prioritizes_important_files(
    inspector,
    sandbox_provider,
    sandbox_session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=(
            "repository/image.png\x00"
            "repository/main.py\x00"
            "repository/README.md\x00"
            "repository/package.json\x00"
        )
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "available"

    assert set(result.files[:2]) == {
        "README.md",
        "package.json",
    }

    assert result.files[2] == "main.py"
    assert result.files[3] == "image.png"
    assert result.truncated is False


def test_inspect_truncates_large_repository(
    sandbox_provider,
    sandbox_session,
):
    inspector = SandboxRepositoryInspector(
        sandbox_provider=sandbox_provider,
        max_repository_files=3,
    )

    files = [
        f"repository/file_{index}.txt"
        for index in range(4)
    ]

    files.append("repository/README.md")

    sandbox_provider.run_command.return_value = make_command_result(
        stdout="\x00".join(files) + "\x00"
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "available"
    assert len(result.files) == 3
    assert result.truncated is True
    assert "README.md" in result.files


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/etc/passwd",
        "../outside.py",
        "repository/../outside.py",
        "other-repository/main.py",
    ],
)
def test_inspect_rejects_unsafe_sandbox_paths(
    inspector,
    sandbox_provider,
    sandbox_session,
    unsafe_path,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=f"{unsafe_path}\x00"
    )

    result = inspector.inspect(sandbox_session)

    assert result.status == "unavailable"
    assert result.files == []
    assert "invalid repository path" in result.error.lower()


def test_inspector_rejects_zero_file_limit(sandbox_provider):
    with pytest.raises(
        ValueError,
        match="Maximum repository file count must be positive",
    ):
        SandboxRepositoryInspector(
            sandbox_provider=sandbox_provider,
            max_repository_files=0,
        )
