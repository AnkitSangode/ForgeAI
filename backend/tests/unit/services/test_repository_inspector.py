from forgeai.services.repository_inspector import RepositoryInspector


def test_inspect_valid_repository(tmp_path):
    # Arrange: create a temporary repository
    repository = tmp_path / "my-project"
    repository.mkdir()

    # Create files in the repository root
    (repository / "README.md").write_text("# My Project")
    (repository / "requirements.txt").write_text("fastapi")

    # Act: inspect the repository
    inspector = RepositoryInspector()
    result = inspector.inspect(str(repository))

    # Assert: verify the result
    assert result.status == "available"
    assert result.error is None
    assert set(result.files) == {
        "README.md",
        "requirements.txt",
    }


def test_inspect_nonexistent_path(tmp_path):
    # Arrange: define a path that does not exist
    repository = tmp_path / "nonexistent"

    # Act
    inspector = RepositoryInspector()
    result = inspector.inspect(str(repository))

    # Assert
    assert result.status == "unavailable"
    assert result.files == []
    assert result.error == "Repository path does not exist."


def test_inspect_file_instead_of_directory(tmp_path):
    # Arrange: create a file instead of a directory
    file_path = tmp_path / "main.py"
    file_path.write_text("print('Hello')")

    # Act
    inspector = RepositoryInspector()
    result = inspector.inspect(str(file_path))

    # Assert
    assert result.status == "unavailable"
    assert result.files == []
    assert result.error == "Repository path is not a directory."


def test_inspect_excludes_unnecessary_directories(tmp_path):
    # Arrange: create a repository
    repository = tmp_path / "my-project"
    repository.mkdir()

    # Create an ordinary source file
    source = repository / "src"
    source.mkdir()
    (source / "main.py").write_text("print('Hello')")

    # Create excluded directories and files
    virtual_env = repository / ".venv"
    virtual_env.mkdir()
    (virtual_env / "library.py").write_text("# Dependency")

    node_modules = repository / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.js").write_text("// Dependency")

    # Act
    inspector = RepositoryInspector()
    result = inspector.inspect(str(repository))

    # Assert
    assert result.status == "available"
    assert set(result.files) == {
        str(source.relative_to(repository) / "main.py"),
    }


def test_inspect_nested_directories(tmp_path):
    # Arrange: create a nested repository structure
    repository = tmp_path / "my-project"

    source = repository / "src" / "services"
    source.mkdir(parents=True)

    (source / "auth.py").write_text("# Authentication")
    (source / "user.py").write_text("# User service")

    # Act
    inspector = RepositoryInspector()
    result = inspector.inspect(str(repository))

    # Assert
    assert result.status == "available"
    assert set(result.files) == {
        str(
            source.relative_to(repository) / "auth.py"
        ),
        str(
            source.relative_to(repository) / "user.py"
        ),
    }