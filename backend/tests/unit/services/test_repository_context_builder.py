from forgeai.services.repository_context_builder import (
    RepositoryContextBuilder,
)


def test_build_context_from_valid_files(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    (repository / "auth.py").write_text(
        "def authenticate(): pass",
        encoding="utf-8",
    )
    (repository / "users.py").write_text(
        "class UserService: pass",
        encoding="utf-8",
    )

    builder = RepositoryContextBuilder()

    result = builder.build(
        str(repository),
        ["auth.py", "users.py"],
    )

    assert result.status == "available"
    assert len(result.files) == 2
    assert result.total_bytes > 0
    assert result.skipped_files == []
    assert result.errors == []


def test_build_context_skips_files_when_byte_budget_is_exceeded(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    (repository / "first.py").write_text("a" * 60, encoding="utf-8")
    (repository / "second.py").write_text("b" * 60, encoding="utf-8")
    (repository / "third.py").write_text("c" * 10, encoding="utf-8")

    builder = RepositoryContextBuilder(max_context_bytes=100)

    result = builder.build(
        str(repository),
        ["first.py", "second.py", "third.py"],
    )

    assert result.status == "partial"
    assert len(result.files) == 1
    assert result.files[0].file_path == "first.py"
    assert result.total_bytes == 60
    assert result.skipped_files == ["second.py", "third.py"]


def test_build_context_respects_maximum_file_count(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    file_paths = []

    for index in range(4):
        filename = f"file_{index}.py"
        (repository / filename).write_text("content", encoding="utf-8")
        file_paths.append(filename)

    builder = RepositoryContextBuilder(max_files=2)

    result = builder.build(str(repository), file_paths)

    assert result.status == "partial"
    assert len(result.files) == 2
    assert result.skipped_files == ["file_2.py", "file_3.py"]


def test_build_context_handles_unreadable_files(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    (repository / "valid.py").write_text("print('Hello')", encoding="utf-8")

    builder = RepositoryContextBuilder()

    result = builder.build(
        str(repository),
        ["missing.py", "valid.py"],
    )

    assert result.status == "partial"
    assert len(result.files) == 1
    assert result.skipped_files == ["missing.py"]
    assert len(result.errors) == 1


def test_build_context_returns_unavailable_when_no_files_are_readable(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    builder = RepositoryContextBuilder()

    result = builder.build(
        str(repository),
        ["missing.py"],
    )

    assert result.status == "unavailable"
    assert result.files == []
    assert result.total_bytes == 0


def test_context_builder_works_with_session_bound_reader():
    import hashlib
    from unittest.mock import Mock

    from forgeai.execution.sandbox.base import SandboxSession
    from forgeai.services.repository_context_builder import (
        RepositoryContextBuilder,
    )
    from forgeai.services.repository_file_read_result import (
        RepositoryFileReadResult,
    )
    from forgeai.services.session_bound_repository_file_reader import (
        SessionBoundRepositoryFileReader,
    )

    content = "def authenticate():\n    return True\n"

    sandbox_reader = Mock()
    sandbox_reader.read.return_value = RepositoryFileReadResult(
        status="available",
        file_path="src/auth.py",
        content=content,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )

    session = SandboxSession(
        sandbox_id="test-sandbox",
        _handle=object(),
    )

    adapter = SessionBoundRepositoryFileReader(
        sandbox_reader=sandbox_reader,
        session=session,
    )

    builder = RepositoryContextBuilder(file_reader=adapter)

    result = builder.build(
        repository_path="repository",
        file_paths=["src/auth.py"],
    )

    assert result.status == "available"
    assert len(result.files) == 1
    assert result.files[0].file_path == "src/auth.py"
    assert result.files[0].content == content
