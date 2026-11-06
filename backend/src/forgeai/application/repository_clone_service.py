
import re
from urllib.parse import urlsplit

from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession
from forgeai.services.repository_clone_result import RepositoryCloneResult


class RepositoryCloneService:
    COMMAND_TIMEOUT_SECONDS = 120
    REPOSITORY_DIRECTORY = "repository"

    def __init__(self, sandbox_provider: SandboxProvider) -> None:
        self.sandbox_provider = sandbox_provider

    @staticmethod
    def _validate_repository_url(repository_url: str) -> str:
        parsed = urlsplit(repository_url)

        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Only HTTPS GitHub repository URLs are supported.")

        parts = parsed.path.strip("/").split("/")

        if (
            len(parts) != 2
            or not all(parts)
            or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts)
        ):
            raise ValueError("Invalid GitHub repository URL.")

        owner, repository = parts

        repository = repository.removesuffix(".git")

        if not owner or not repository:
            raise ValueError("Invalid GitHub repository URL.")

        return f"https://github.com/{owner}/{repository}.git"

    def clone(
        self,
        session: SandboxSession,
        repository_url: str,
    ) -> RepositoryCloneResult:
        clone_url = self._validate_repository_url(repository_url)

        if self.sandbox_provider.file_exists(
            session,
            self.REPOSITORY_DIRECTORY,
        ):
            raise PatchApplicationError(
                "Repository destination already exists in the sandbox."
            )

        # The URL has been validated and its characters are restricted.
        command = (
            f"git clone --depth 1 -- "
            f"'{clone_url}' '{self.REPOSITORY_DIRECTORY}'"
        )

        result = self.sandbox_provider.run_command(
            session=session,
            command=command,
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError(
                f"Repository cloning failed: {result.stderr[:1000]}"
            )

        commit_result = self.sandbox_provider.run_command(
            session=session,
            command="git -C repository rev-parse HEAD",
            timeout_seconds=30,
        )

        if commit_result.exit_code != 0:
            raise PatchApplicationError(
                "Could not determine the cloned repository commit."
            )

        return RepositoryCloneResult(
            repository_name=clone_url.rstrip("/").split("/")[-1].removesuffix(".git"),
            repository_path=self.REPOSITORY_DIRECTORY,
            commit_sha=commit_result.stdout.strip(),
            remote_url=clone_url,
        )
