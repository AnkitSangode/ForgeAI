from unittest.mock import Mock

import pytest

from forgeai.execution.sandbox.base import SandboxSession
from forgeai.services.repository_context_builder import (
    RepositoryContextBuilder,
)
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
def context_builder(
    sandbox_reader: Mock,
    sandbox_session: SandboxSession,
) -> RepositoryContextBuilder:
    session_bound_reader = SessionBoundRepositoryFileReader(
        sandbox_reader=sandbox_reader,
        session=sandbox_session,
    )

    return RepositoryContextBuilder(
        file_reader=session_bound_reader,
    )


def test_build_reads_files_through_bound_sandbox_session(
    sandbox_reader: Mock,
    sandbox_session: SandboxSession,
    context_builder: RepositoryContextBuilder,
) -> None:
    sandbox_reader.read.side_effect = [
        RepositoryFileReadResult(
            status="available",
            file_path="README.md",
            content="# ForgeAI",
            sha256="a" * 64,
            error=None,
            truncated=False,
        ),
        RepositoryFileReadResult(
            status="available",
            file_path="src/main.py",
            content="print('Hello')",
            sha256="b" * 64,
            error=None,
            truncated=False,
        ),
    ]

    result = context_builder.build(
        repository_path="repository",
        file_paths=["README.md", "src/main.py"],
    )

    assert result.status == "available"
    assert len(result.files) == 2
    assert result.files[0].file_path == "README.md"
    assert result.files[0].content == "# ForgeAI"
    assert result.files[1].file_path == "src/main.py"

    assert sandbox_reader.read.call_count == 2

    for call in sandbox_reader.read.call_args_list:
        assert call.kwargs["session"] is sandbox_session
        assert call.kwargs["repository_path"] == "repository"


def test_build_preserves_unavailable_file_errors(
    sandbox_reader: Mock,
    context_builder: RepositoryContextBuilder,
) -> None:
    sandbox_reader.read.side_effect = [
        RepositoryFileReadResult(
            status="available",
            file_path="README.md",
            content="# ForgeAI",
            sha256="a" * 64,
            error=None,
            truncated=False,
        ),
        RepositoryFileReadResult(
            status="unavailable",
            file_path="src/missing.py",
            content=None,
            sha256=None,
            error="File does not exist.",
            truncated=False,
        ),
    ]

    result = context_builder.build(
        repository_path="repository",
        file_paths=["README.md", "src/missing.py"],
    )

    assert result.status == "partial"
    assert len(result.files) == 1
    assert result.skipped_files == ["src/missing.py"]
    assert result.errors == ["src/missing.py: File does not exist."]


def test_build_enforces_context_file_limit(
    sandbox_reader: Mock,
    context_builder: RepositoryContextBuilder,
) -> None:
    builder = RepositoryContextBuilder(
        file_reader=context_builder.file_reader,
        max_files=1,
    )

    sandbox_reader.read.return_value = RepositoryFileReadResult(
        status="available",
        file_path="README.md",
        content="# ForgeAI",
        sha256="a" * 64,
        error=None,
        truncated=False,
    )

    result = builder.build(
        repository_path="repository",
        file_paths=["README.md", "src/main.py"],
    )

    assert result.status == "partial"
    assert len(result.files) == 1
    assert result.skipped_files == ["src/main.py"]

    # The second file should not be read after reaching the limit.
    assert sandbox_reader.read.call_count == 1


def test_build_enforces_context_byte_limit(
    sandbox_reader: Mock,
    context_builder: RepositoryContextBuilder,
) -> None:
    builder = RepositoryContextBuilder(
        file_reader=context_builder.file_reader,
        max_context_bytes=5,
    )

    sandbox_reader.read.return_value = RepositoryFileReadResult(
        status="available",
        file_path="README.md",
        content="123456",
        sha256="a" * 64,
        error=None,
        truncated=False,
    )

    result = builder.build(
        repository_path="repository",
        file_paths=["README.md"],
    )

    assert result.status == "unavailable"
    assert result.files == []
    assert result.total_bytes == 0
    assert result.skipped_files == ["README.md"]

    # The file was read, but rejected because it exceeded the budget.
    sandbox_reader.read.assert_called_once()
