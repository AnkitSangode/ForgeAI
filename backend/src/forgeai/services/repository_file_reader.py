import hashlib
from pathlib import Path

from forgeai.services.repository_file_read_result import (
    RepositoryFileReadResult,
)

MAX_FILE_SIZE_BYTES = 100 * 1024


class RepositoryFileReader:
    """Safely reads text files from a local repository."""

    def read(
        self,
        repository_path: str,
        file_path: str,
    ) -> RepositoryFileReadResult:
        """Read a repository file using a repository-relative path."""

        try:
            repository_root = Path(repository_path).resolve(strict=True)

            if not repository_root.is_dir():
                return self._failure(
                    file_path,
                    "Repository path is not a directory.",
                )

            requested_path = Path(file_path)

            if requested_path.is_absolute() or ".." in requested_path.parts:
                return self._failure(
                    file_path,
                    "Invalid repository-relative file path.",
                )

            candidate_path = repository_root / requested_path
            current_path = repository_root

            for part in requested_path.parts:
                current_path = current_path / part

                if current_path.is_symlink():
                    return self._failure(
                        file_path,
                        "Symbolic links are not allowed.",
                    )

            resolved_path = candidate_path.resolve(strict=True)

            try:
                resolved_path.relative_to(repository_root)
            except ValueError:
                return self._failure(
                    file_path,
                    "File path escapes the repository directory.",
                )

            if not resolved_path.is_file():
                return self._failure(
                    file_path,
                    "Requested path is not a file.",
                )

            with resolved_path.open("rb") as file:
                content_bytes = file.read(MAX_FILE_SIZE_BYTES + 1)

            if len(content_bytes) > MAX_FILE_SIZE_BYTES:
                return self._failure(
                    file_path,
                    "File exceeds the maximum allowed size of 100 KB.",
                )

            content = content_bytes.decode("utf-8")
            file_hash = hashlib.sha256(content_bytes).hexdigest()

            return RepositoryFileReadResult(
                status="available",
                file_path=requested_path.as_posix(),
                content=content,
                sha256=file_hash,
            )

        except FileNotFoundError:
            return self._failure(
                file_path,
                "File does not exist.",
            )

        except UnicodeDecodeError:
            return self._failure(
                file_path,
                "File is not valid UTF-8 text.",
            )

        except (OSError, RuntimeError):
            return self._failure(
                file_path,
                "Unable to read the requested file.",
            )

    @staticmethod
    def _failure(
        file_path: str,
        error: str,
    ) -> RepositoryFileReadResult:
        """Create a consistent failed reading result."""

        return RepositoryFileReadResult(
            status="unavailable",
            file_path=file_path,
            error=error,
        )
