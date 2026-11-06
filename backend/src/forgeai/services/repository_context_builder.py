from typing import Protocol

from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)
from forgeai.services.repository_file_read_result import (
    RepositoryFileReadResult,
)
from forgeai.services.repository_file_reader import RepositoryFileReader


MAX_CONTEXT_FILES = 20
MAX_CONTEXT_BYTES = 500 * 1024


class RepositoryFileReaderProtocol(Protocol):
    """Contract required by the repository context builder."""

    def read(
        self,
        repository_path: str,
        file_path: str,
    ) -> RepositoryFileReadResult:
        ...


class RepositoryContextBuilder:
    """Builds bounded repository context from selected files."""

    def __init__(
        self,
        file_reader: RepositoryFileReaderProtocol | None = None,
        max_files: int = MAX_CONTEXT_FILES,
        max_context_bytes: int = MAX_CONTEXT_BYTES,
    ) -> None:
        if max_files <= 0:
            raise ValueError("Maximum file count must be greater than zero.")

        if max_context_bytes <= 0:
            raise ValueError("Maximum context size must be greater than zero.")

        self.file_reader = file_reader or RepositoryFileReader()
        self.max_files = max_files
        self.max_context_bytes = max_context_bytes

    def build(
        self,
        repository_path: str,
        file_paths: list[str],
    ) -> RepositoryContextResult:
        """Read selected files and build a bounded repository context."""

        collected_files: list[RepositoryFileContext] = []
        skipped_files: list[str] = []
        errors: list[str] = []
        total_bytes = 0

        for index, file_path in enumerate(file_paths):
            if len(collected_files) >= self.max_files:
                skipped_files.extend(file_paths[index:])
                break

            result = self.file_reader.read(
                repository_path=repository_path,
                file_path=file_path,
            )

            if result.status == "unavailable":
                skipped_files.append(file_path)
                errors.append(
                    f"{file_path}: "
                    f"{result.error or 'Unable to read file.'}"
                )
                continue

            content = result.content or ""
            content_bytes = len(content.encode("utf-8"))

            if total_bytes + content_bytes > self.max_context_bytes:
                skipped_files.extend(file_paths[index:])
                break

            if result.sha256 is None:
                skipped_files.append(file_path)
                errors.append(
                    f"{file_path}: "
                    "File reader did not provide a SHA-256 snapshot."
                )
                continue

            collected_files.append(
                RepositoryFileContext(
                    file_path=result.file_path,
                    content=content,
                    sha256=result.sha256,
                )
            )

            total_bytes += content_bytes

        if not collected_files:
            status = "unavailable"
        elif skipped_files or errors:
            status = "partial"
        else:
            status = "available"

        return RepositoryContextResult(
            status=status,
            files=collected_files,
            total_bytes=total_bytes,
            skipped_files=skipped_files,
            errors=errors,
        )