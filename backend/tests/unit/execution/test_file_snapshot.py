from pathlib import Path

import pytest
from pydantic import ValidationError

from forgeai.execution.exceptions import (
    FileIntegrityError,
    FileSnapshotError,
)
from forgeai.execution.file_snapshot import FileSnapshotService
from forgeai.execution.schemas import FileSnapshot


@pytest.fixture
def snapshot_service() -> FileSnapshotService:
    return FileSnapshotService()


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    (source_dir / "auth.py").write_text(
        "def authenticate(token):\n    return True\n",
        encoding="utf-8",
    )

    return tmp_path


def test_create_snapshot(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    snapshot = snapshot_service.create_snapshot(
        repository_root,
        "src/auth.py",
    )

    assert snapshot.file_path == "src/auth.py"
    assert len(snapshot.sha256) == 64
    assert all(char in "0123456789abcdef" for char in snapshot.sha256)


def test_verify_unchanged_file(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    snapshot = snapshot_service.create_snapshot(
        repository_root,
        "src/auth.py",
    )

    snapshot_service.verify_snapshot(repository_root, snapshot)


def test_detect_modified_file(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    snapshot = snapshot_service.create_snapshot(
        repository_root,
        "src/auth.py",
    )

    (repository_root / "src" / "auth.py").write_text(
        "def authenticate(token):\n    return False\n",
        encoding="utf-8",
    )

    with pytest.raises(FileIntegrityError, match="has changed"):
        snapshot_service.verify_snapshot(repository_root, snapshot)


def test_detect_deleted_file(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    snapshot = snapshot_service.create_snapshot(
        repository_root,
        "src/auth.py",
    )

    (repository_root / "src" / "auth.py").unlink()

    with pytest.raises(FileIntegrityError):
        snapshot_service.verify_snapshot(repository_root, snapshot)


def test_reject_missing_file(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    with pytest.raises(FileSnapshotError):
        snapshot_service.create_snapshot(
            repository_root,
            "src/missing.py",
        )


@pytest.mark.parametrize(
    "file_path",
    [
        "../../.env",
        "/etc/passwd",
        r"C:\Windows\system.ini",
        r"src\auth.py",
        "",
    ],
)
def test_reject_unsafe_paths(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
    file_path: str,
) -> None:
    with pytest.raises(FileSnapshotError):
        snapshot_service.create_snapshot(
            repository_root,
            file_path,
        )


def test_create_multiple_snapshots(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    (repository_root / "src" / "config.py").write_text(
        "DEBUG = False\n",
        encoding="utf-8",
    )

    snapshots = snapshot_service.create_snapshots(
        repository_root,
        ["src/auth.py", "src/config.py"],
    )

    assert len(snapshots) == 2
    assert snapshots[0].file_path == "src/auth.py"
    assert snapshots[1].file_path == "src/config.py"


def test_reject_duplicate_snapshot_paths(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    with pytest.raises(FileSnapshotError, match="Duplicate"):
        snapshot_service.create_snapshots(
            repository_root,
            ["src/auth.py", "src/auth.py"],
        )


def test_reject_empty_snapshot_list(
    snapshot_service: FileSnapshotService,
    repository_root: Path,
) -> None:
    with pytest.raises(FileSnapshotError):
        snapshot_service.create_snapshots(
            repository_root,
            [],
        )


def test_snapshot_is_immutable() -> None:
    snapshot = FileSnapshot(
        file_path="src/auth.py",
        sha256="a" * 64,
    )

    with pytest.raises(ValidationError):
        snapshot.sha256 = "b" * 64
