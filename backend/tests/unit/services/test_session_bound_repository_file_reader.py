from unittest.mock import Mock

import pytest

from forgeai.execution.sandbox.base import SandboxSession
from forgeai.services.repository_file_read_result import (
    RepositoryFileReadResult,
)
from forgeai.services.sandbox_repository_file_reader import (
    SandboxRepositoryFileReader,
)
from forgeai.services.session_bound_repository_file_reader import (
    SessionBoundRepositoryFileReader,
)


@pytest.fixture
def sandbox_session() -> SandboxSession:
    return SandboxSession(
        sandbox_id="sandbox-123",
        _handle=object(),
    )


@pytest.fixture
def sandbox_reader() -> Mock:
    return Mock(spec=SandboxRepositoryFileReader)


@pytest.fixture
def session_bound_reader(
    sandbox_reader: Mock,
    sandbox_session: SandboxSession,
) -> SessionBoundRepositoryFileReader:
    return SessionBoundRepositoryFileReader(
        sandbox_reader=sandbox_reader,
        session=sandbox_session,
    )


def test_read_delegates_to_sandbox_reader(
    sandbox_reader: Mock,
    sandbox_session: SandboxSession,
    session_bound_reader: SessionBoundRepositoryFileReader,
) -> None:
    expected_result = RepositoryFileReadResult(
        status="available",
        file_path="src/main.py",
        content="print('Hello ForgeAI')",
        sha256="a" * 64,
        error=None,
        truncated=False,
    )
    sandbox_reader.read.return_value = expected_result

    result = session_bound_reader.read(
        repository_path="repository",
        file_path="src/main.py",
    )

    assert result == expected_result

    sandbox_reader.read.assert_called_once_with(
        session=sandbox_session,
        repository_path="repository",
        file_path="src/main.py",
    )


def test_read_returns_unavailable_result_from_sandbox_reader(
    sandbox_reader: Mock,
    session_bound_reader: SessionBoundRepositoryFileReader,
) -> None:
    expected_result = RepositoryFileReadResult(
        status="unavailable",
        file_path="src/missing.py",
        content=None,
        sha256=None,
        error="File does not exist.",
        truncated=False,
    )
    sandbox_reader.read.return_value = expected_result

    result = session_bound_reader.read(
        repository_path="repository",
        file_path="src/missing.py",
    )

    assert result == expected_result
    sandbox_reader.read.assert_called_once()


def test_read_reuses_the_bound_sandbox_session(
    sandbox_reader: Mock,
    sandbox_session: SandboxSession,
    session_bound_reader: SessionBoundRepositoryFileReader,
) -> None:
    sandbox_reader.read.return_value = RepositoryFileReadResult(
        status="available",
        file_path="src/first.py",
        content="first",
        sha256="a" * 64,
        error=None,
        truncated=False,
    )

    session_bound_reader.read(
        repository_path="repository",
        file_path="src/first.py",
    )
    session_bound_reader.read(
        repository_path="repository",
        file_path="src/second.py",
    )

    assert sandbox_reader.read.call_count == 2

    for call in sandbox_reader.read.call_args_list:
        assert call.kwargs["session"] is sandbox_session
