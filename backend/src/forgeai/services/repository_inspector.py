import os

from forgeai.services.repository_inspection_result import (
    RepositoryInspectionResult,
)

EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}


class RepositoryInspector:
    """Inspects a local repository and returns its file information."""

    def inspect(self, repository_path: str) -> RepositoryInspectionResult:
        if not os.path.exists(repository_path):
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error="Repository path does not exist.",
            )

        if not os.path.isdir(repository_path):
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error="Repository path is not a directory.",
            )

        repository_files: list[str] = []

        try:
            repository_root = os.path.realpath(repository_path)

            for root, directories, files in os.walk(
                repository_root,
                topdown=True,
                followlinks=False,
            ):
                directories[:] = [
                    directory
                    for directory in directories
                    if directory not in EXCLUDED_DIRECTORIES
                    and not os.path.islink(os.path.join(root, directory))
                ]

                for filename in files:
                    absolute_path = os.path.join(root, filename)

                    if os.path.islink(absolute_path):
                        continue

                    relative_path = os.path.relpath(
                        absolute_path,
                        repository_root,
                    )

                    repository_files.append(relative_path)

            return RepositoryInspectionResult(
                status="available",
                files=repository_files,
            )

        except OSError as exc:
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error=f"Repository inspection failed: {exc}",
            )
