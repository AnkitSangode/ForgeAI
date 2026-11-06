from unittest.mock import Mock

import pytest

from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxFileResult,
    SandboxSession,
)
from forgeai.services.sandbox_repository_file_reader import (
    SandboxRepositoryFileReader,
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
def reader(sandbox_provider):
    return SandboxRepositoryFileReader(sandbox_provider)


def command_result(stdout="", stderr="", exit_code=0):
    return CommandExecutionResult(
        command="test command",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def configure_valid_file(sandbox_provider, content):
    content_bytes = content.encode("utf-8")

    sandbox_provider.run_command.side_effect = [
        command_result(stdout="file"),
        command_result(stdout=str(len(content_bytes))),
    ]

    import hashlib

    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="repository/src/main.py",
        content=content,
        sha256=hashlib.sha256(content_bytes).hexdigest(),
    )


def test_reads_file_successfully(
    reader,
    sandbox_provider,
    session,
):
    configure_valid_file(
        sandbox_provider,
        "print('Hello ForgeAI')\n",
    )

    result = reader.read(
        session,
        "repository",
        "src/main.py",
    )

    assert result.status == "available"
    assert result.content == "print('Hello ForgeAI')\n"
    assert result.sha256 is not None
    assert result.file_path == "src/main.py"


def test_rejects_invalid_repository_path(
    reader,
    session,
):
    result = reader.read(
        session,
        "other",
        "src/main.py",
    )

    assert result.status == "unavailable"


@pytest.mark.parametrize(
    "file_path",
    [
        "../secret.txt",
        "/etc/passwd",
        "src/../../secret.txt",
        r"src\main.py",
    ],
)
def test_rejects_unsafe_file_paths(
    reader,
    session,
    file_path,
):
    result = reader.read(
        session,
        "repository",
        file_path,
    )

    assert result.status == "unavailable"


def test_rejects_symbolic_link(
    reader,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.return_value = command_result(
        stdout="symlink",
    )

    result = reader.read(
        session,
        "repository",
        "src/main.py",
    )

    assert result.status == "unavailable"
    assert "Symbolic links" in result.error
    sandbox_provider.read_file.assert_not_called()


def test_rejects_missing_file(
    reader,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.return_value = command_result(
        stdout="unavailable",
    )

    result = reader.read(
        session,
        "repository",
        "src/missing.py",
    )

    assert result.status == "unavailable"
    sandbox_provider.read_file.assert_not_called()


def test_rejects_file_exceeding_size_limit(
    reader,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.side_effect = [
        command_result(stdout="file"),
        command_result(stdout="102401"),
    ]

    result = reader.read(
        session,
        "repository",
        "src/large.py",
    )

    assert result.status == "unavailable"
    assert "exceeds" in result.error
    sandbox_provider.read_file.assert_not_called()


def test_rejects_hash_mismatch(
    reader,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.side_effect = [
        command_result(stdout="file"),
        command_result(stdout="5"),
    ]

    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="repository/src/main.py",
        content="hello",
        sha256="invalid-hash",
    )

    result = reader.read(
        session,
        "repository",
        "src/main.py",
    )

    assert result.status == "unavailable"
    assert "hash verification" in result.error


def test_rejects_file_changed_during_read(
    reader,
    sandbox_provider,
    session,
):
    configure_valid_file(
        sandbox_provider,
        "changed",
    )

    # Report the original size, but return different-sized content.
    sandbox_provider.run_command.side_effect = [
        command_result(stdout="file"),
        command_result(stdout="5"),
    ]

    result = reader.read(
        session,
        "repository",
        "src/main.py",
    )

    assert result.status == "unavailable"
    assert "changed while" in result.error


def test_handles_provider_failure(
    reader,
    sandbox_provider,
    session,
):
    sandbox_provider.run_command.side_effect = RuntimeError(
        "Sandbox unavailable"
    )

    result = reader.read(
        session,
        "repository",
        "src/main.py",
    )

    assert result.status == "unavailable"
    assert "Sandbox unavailable" in result.error


def test_requires_positive_file_size_limit(
    sandbox_provider,
):
    with pytest.raises(ValueError):
        SandboxRepositoryFileReader(
            sandbox_provider,
            max_file_size_bytes=0,
        )