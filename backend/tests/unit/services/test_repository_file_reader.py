from forgeai.services.repository_file_reader import (
    MAX_FILE_SIZE_BYTES,
    RepositoryFileReader,
)



def test_read_valid_repository_file(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    source_file = repository / "main.py"
    source_file.write_text(
        "print('Hello ForgeAI')",
        encoding="utf-8",
    )

    reader = RepositoryFileReader()

    result = reader.read(str(repository), "main.py")

    assert result.status == "available"
    assert result.content == "print('Hello ForgeAI')"
    assert result.error is None


def test_read_nonexistent_file(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    reader = RepositoryFileReader()

    result = reader.read(str(repository), "missing.py")

    assert result.status == "unavailable"
    assert result.error == "File does not exist."


def test_reject_directory_traversal(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    reader = RepositoryFileReader()

    result = reader.read(str(repository), "../secret.txt")

    assert result.status == "unavailable"
    assert result.error == "Invalid repository-relative file path."


def test_reject_oversized_file(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    source_file = repository / "large.py"
    source_file.write_bytes(b"a" * (MAX_FILE_SIZE_BYTES + 1))

    reader = RepositoryFileReader()

    result = reader.read(str(repository), "large.py")

    assert result.status == "unavailable"
    assert "maximum allowed size" in result.error


def test_reject_invalid_utf8_file(tmp_path):
    repository = tmp_path / "project"
    repository.mkdir()

    source_file = repository / "invalid.py"
    source_file.write_bytes(b"\xff\xfe\xfa")

    reader = RepositoryFileReader()

    result = reader.read(str(repository), "invalid.py")

    assert result.status == "unavailable"
    assert result.error == "File is not valid UTF-8 text."
