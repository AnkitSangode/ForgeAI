import hashlib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath, PureWindowsPath

from forgeai.execution.exceptions import (
    FileIntegrityError,
    FileSnapshotError,
)
from forgeai.execution.schemas import FileSnapshot


class FileSnapshotService:
    """Creates and verifies trusted SHA-256 repository file snapshots."""

    def create_snapshot(
        self,
        repository_root: Path,
        file_path: str,
    ) -> FileSnapshot:
        """Create a SHA-256 snapshot of one existing repository file."""

        target = self._resolve_file(repository_root, file_path)

        try:
            file_hash = self._calculate_sha256(target)
        except OSError as exc:
            raise FileSnapshotError(f"Unable to read file for snapshot: {file_path}") from exc

        return FileSnapshot(
            file_path=file_path,
            sha256=file_hash,
        )

    def create_snapshots(
        self,
        repository_root: Path,
        file_paths: Iterable[str],
    ) -> list[FileSnapshot]:
        """Create snapshots for multiple files."""

        paths = list(file_paths)

        if not paths:
            raise FileSnapshotError("At least one file path is required.")

        if len(paths) != len(set(paths)):
            raise FileSnapshotError("Duplicate file paths are not permitted.")

        return [self.create_snapshot(repository_root, file_path) for file_path in paths]

    def verify_snapshot(
        self,
        repository_root: Path,
        snapshot: FileSnapshot,
    ) -> None:
        """
        Verify that a file still matches its original snapshot.

        Returns None when the file is unchanged.
        Raises FileIntegrityError when it is missing or modified.
        """

        try:
            target = self._resolve_file(
                repository_root,
                snapshot.file_path,
            )
            current_hash = self._calculate_sha256(target)

        except (FileSnapshotError, OSError) as exc:
            raise FileIntegrityError(f"Cannot verify file integrity: {snapshot.file_path}") from exc

        if current_hash != snapshot.sha256:
            raise FileIntegrityError(f"File has changed since its snapshot: {snapshot.file_path}")

    @staticmethod
    def _resolve_file(
        repository_root: Path,
        file_path: str,
    ) -> Path:
        """Resolve a repository file while rejecting unsafe paths."""

        if not isinstance(file_path, str) or not file_path.strip():
            raise FileSnapshotError("File path cannot be blank.")

        if "\x00" in file_path or "\\" in file_path:
            raise FileSnapshotError("Invalid repository file path.")

        windows_path = PureWindowsPath(file_path)
        posix_path = PurePosixPath(file_path)

        if windows_path.is_absolute() or windows_path.drive or posix_path.is_absolute():
            raise FileSnapshotError(f"Absolute paths are not permitted: {file_path}")

        if any(part in {"", ".", ".."} for part in file_path.split("/")):
            raise FileSnapshotError(f"Invalid relative path: {file_path}")

        if posix_path.as_posix() != file_path:
            raise FileSnapshotError(f"Path is not canonical: {file_path}")

        try:
            root = repository_root.resolve(strict=True)
        except OSError as exc:
            raise FileSnapshotError("Repository root does not exist.") from exc

        if not root.is_dir():
            raise FileSnapshotError("Repository root must be a directory.")

        target = root

        for part in file_path.split("/"):
            target = target / part

            if target.is_symlink():
                raise FileSnapshotError(f"Symlink paths are not permitted: {file_path}")

        try:
            resolved_target = target.resolve(strict=True)
            resolved_target.relative_to(root)
        except (OSError, ValueError) as exc:
            raise FileSnapshotError(
                f"File is missing or outside the repository: {file_path}"
            ) from exc

        if not resolved_target.is_file():
            raise FileSnapshotError(f"Target is not a regular file: {file_path}")

        return resolved_target

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA-256 using bounded-memory file reading."""

        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while chunk := file.read(64 * 1024):
                digest.update(chunk)

        return digest.hexdigest()
