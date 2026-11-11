from unittest.mock import Mock

import pytest

from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxSession,
)
from forgeai.services.repository_inspector import (
    SandboxRepositoryInspector,
)


@pytest.fixture
def sandbox_provider():
    return Mock()


@pytest.fixture
def session():
    return SandboxSession(
        sandbox_id="test-sandbox",
        _handle=object(),
    )


@pytest.fixture
def inspector(sandbox_provider):
    return SandboxRepositoryInspector(
        sandbox_provider=sandbox_provider,
    )


def make_command_result(
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
) -> CommandExecutionResult:
    return CommandExecutionResult(
        command="find repository",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def test_inspect_returns_repository_relative_paths(
    inspector,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=("repository/README.md\x00repository/src/main.py\x00")
    )

    result = inspector.inspect(session)

    assert result.status == "available"
    assert result.files == [
        "README.md",
        "src/main.py",
    ]
    assert result.truncated is False


def test_inspect_prioritizes_important_files(
    inspector,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stdout=(
            "repository/src/main.py\x00"
            "repository/README.md\x00"
            "repository/tests/test_main.py\x00"
            "repository/notes.txt\x00"
        )
    )

    result = inspector.inspect(session)

    assert result.files == [
        "README.md",
        "src/main.py",
        "tests/test_main.py",
        "notes.txt",
    ]


def test_inspect_truncates_file_list(
    sandbox_provider,
    session,
):
    inspector = SandboxRepositoryInspector(
        sandbox_provider=sandbox_provider,
        max_repository_files=2,
    )

    sandbox_provider.run_command.return_value = make_command_result(
        stdout=("repository/a.py\x00repository/b.py\x00repository/c.py\x00")
    )

    result = inspector.inspect(session)

    assert result.status == "available"
    assert len(result.files) == 2
    assert result.truncated is True


def test_inspect_returns_unavailable_when_command_fails(
    inspector,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.return_value = make_command_result(
        stderr="Repository not found",
        exit_code=1,
    )

    result = inspector.inspect(session)

    assert result.status == "unavailable"
    assert result.files == []
    assert "Repository not found" in result.error


@pytest.mark.parametrize(
    "invalid_path",
    [
        "/repository/main.py",
        "../repository/main.py",
        "other/main.py",
        "repository/../main.py",
    ],
)
def test_inspect_rejects_invalid_paths(
    inspector,
    sandbox_provider,
    session,
    invalid_path,
):
    sandbox_provider.run_command.return_value = make_command_result(stdout=f"{invalid_path}\x00")

    result = inspector.inspect(session)

    assert result.status == "unavailable"
    assert result.files == []


def test_inspect_rejects_non_repository_root(
    inspector,
    session,
):
    result = inspector.inspect(
        session,
        repository_path="other",
    )

    assert result.status == "unavailable"
    assert result.files == []


def test_inspect_handles_provider_exception(
    inspector,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.side_effect = RuntimeError("Sandbox unavailable")

    result = inspector.inspect(session)

    assert result.status == "unavailable"
    assert result.files == []
    assert "Sandbox unavailable" in result.error


def test_inspector_requires_positive_file_limit(
    sandbox_provider,
):
    with pytest.raises(ValueError):
        SandboxRepositoryInspector(
            sandbox_provider=sandbox_provider,
            max_repository_files=0,
        )
