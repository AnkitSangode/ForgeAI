
import pytest

from forgeai.execution.repository_paths import (
    resolve_repository_file_path,
)


def test_resolves_repository_file_path():
    assert (
        resolve_repository_file_path("src/main.py")
        == "repository/src/main.py"
    )


def test_resolves_nested_repository_path():
    assert (
        resolve_repository_file_path("src/services/auth.py")
        == "repository/src/services/auth.py"
    )


@pytest.mark.parametrize(
    "file_path",
    [
        "",
        "../outside.py",
        "src/../../outside.py",
        "/etc/passwd",
        r"src\main.py",
        "src/./main.py",
        "src//main.py",
        "src/\x00main.py",
    ],
)
def test_rejects_unsafe_repository_paths(file_path):
    with pytest.raises(ValueError):
        resolve_repository_file_path(file_path)
