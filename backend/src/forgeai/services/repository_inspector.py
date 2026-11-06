from pathlib import PurePosixPath

from forgeai.execution.sandbox.base import (
    SandboxProvider,
    SandboxSession,
)
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


class SandboxRepositoryInspector:
    """Inspects a cloned repository inside a remote sandbox."""

    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        max_repository_files: int = MAX_REPOSITORY_FILES,
    ) -> None:
        if max_repository_files <= 0:
            raise ValueError(
                "Maximum repository file count must be positive."
            )

        self.sandbox_provider = sandbox_provider
        self.max_repository_files = max_repository_files

    def inspect(
        self,
        session: SandboxSession,
        repository_path: str = "repository",
    ) -> RepositoryInspectionResult:
        """Discover repository files inside the sandbox."""

        if repository_path != "repository":
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error="Repository path must be the configured repository directory.",
            )

        excluded_names = " ".join(
            f"-name {name}" for name in sorted(EXCLUDED_DIRECTORIES)
        )

        prune_expression = " -o ".join(
            f"-name {name}" for name in sorted(EXCLUDED_DIRECTORIES)
        )

        command = (
            "find repository "
            f"\\( -type d \\( {prune_expression} \\) -prune \\) "
            "-o "
            "\\( -type f ! -type l -print0 \\)"
        )

        try:
            result = self.sandbox_provider.run_command(
                session=session,
                command=command,
                timeout_seconds=30,
            )

            if result.exit_code != 0:
                return RepositoryInspectionResult(
                    status="unavailable",
                    files=[],
                    error=(
                        "Repository inspection failed: "
                        f"{result.stderr.strip() or 'find command failed.'}"
                    ),
                )

            repository_files = self._parse_file_paths(result.stdout)

            prioritized_files = sorted(
                repository_files,
                key=lambda file_path: (
                    self._get_file_priority(file_path),
                    file_path.lower(),
                ),
            )

            truncated = (
                len(prioritized_files) > self.max_repository_files
            )

            selected_files = prioritized_files[
                : self.max_repository_files
            ]

            return RepositoryInspectionResult(
                status="available",
                files=selected_files,
                truncated=truncated,
            )

        except (OSError, RuntimeError, ValueError) as exc:
            return RepositoryInspectionResult(
                status="unavailable",
                files=[],
                error=f"Repository inspection failed: {exc}",
            )

    @staticmethod
    def _parse_file_paths(stdout: str) -> list[str]:
        """Convert NUL-separated sandbox paths into repository-relative paths."""

        repository_files: list[str] = []

        for raw_path in stdout.split("\x00"):
            if not raw_path:
                continue

            path = PurePosixPath(raw_path)

            if (
                path.is_absolute()
                or not path.parts
                or path.parts[0] != "repository"
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise ValueError(
                    f"Sandbox returned an invalid repository path: {raw_path}"
                )

            relative_path = PurePosixPath(*path.parts[1:])

            if not relative_path.parts:
                continue

            repository_files.append(relative_path.as_posix())

        return repository_files

    @staticmethod
    def _get_file_priority(file_path: str) -> int:
        filename = PurePosixPath(file_path).name
        path_parts = PurePosixPath(file_path).parts

        if filename in IMPORTANT_FILES:
            return 1

        if file_path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            if "tests" in path_parts:
                return 3

            return 2

        if "tests" in path_parts:
            return 3

        return 4