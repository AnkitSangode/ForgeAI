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

MAX_REPOSITORY_FILES = 5000

IMPORTANT_FILES = {
    "README.md",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "tsconfig.json",
    "alembic.ini",
    "Dockerfile",
    ".env.example",
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

            prioritized_files = sorted(
                repository_files,
                key=lambda file_path: (
                    self._get_file_priority(file_path),
                    file_path.lower(),
                ),
            )

            truncated = len(prioritized_files) > MAX_REPOSITORY_FILES

            selected_files = prioritized_files[:MAX_REPOSITORY_FILES]

            return RepositoryInspectionResult(
                status="available",
                files=selected_files,
                truncated=truncated,
            )

        except OSError as exc:
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error=f"Repository inspection failed: {exc}",
            )

    @staticmethod
    def _get_file_priority(file_path: str) -> int:
        filename = os.path.basename(file_path)

        if filename in IMPORTANT_FILES:
            return 1

        if file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            if "tests" in file_path.lower().split(os.sep):
                return 3
            return 2

        if "tests" in file_path.lower().split(os.sep):
            return 3

        return 4
