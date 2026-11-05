from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import FileIntegrityError
from forgeai.execution.sandbox.base import (
    SandboxProvider,
    SandboxSession,
)
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
)


class FileIntegrityVerifier:
    """Verifies that sandbox files have not changed since inspection."""

    def __init__(self, sandbox_provider: SandboxProvider) -> None:
        self.sandbox_provider = sandbox_provider

    def verify(
        self,
        session: SandboxSession,
        changes: list[CodeChange],
        repository_context: RepositoryContextResult,
    ) -> None:
        """Verify all proposed changes against the original repository context."""

        if not changes:
            raise FileIntegrityError("Cannot verify integrity: no code changes were provided.")

        original_files = {file.file_path: file for file in repository_context.files}

        for change in changes:
            file_path = change.file_path

            if change.change_type == "create":
                self._verify_create(session, file_path)
                continue

            if change.change_type in {"modify", "delete"}:
                self._verify_existing_file(
                    session=session,
                    file_path=file_path,
                    original_files=original_files,
                )
                continue

            raise FileIntegrityError(
                f"Unsupported change type for '{file_path}': {change.change_type}"
            )

    def _verify_create(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> None:
        """Ensure a file proposed for creation does not already exist."""

        if self.sandbox_provider.file_exists(session, file_path):
            raise FileIntegrityError(f"Cannot create '{file_path}': the file already exists.")

    def _verify_existing_file(
        self,
        session: SandboxSession,
        file_path: str,
        original_files: dict,
    ) -> None:
        """Compare the current remote file hash with its original hash."""

        original_file = original_files.get(file_path)

        if original_file is None:
            raise FileIntegrityError(
                f"Cannot verify '{file_path}': no original repository snapshot is available."
            )

        if not self.sandbox_provider.file_exists(session, file_path):
            raise FileIntegrityError(
                f"Cannot modify or delete '{file_path}': the file no longer exists in the sandbox."
            )

        current_file = self.sandbox_provider.read_file(
            session,
            file_path,
        )

        if current_file.sha256 is None:
            raise FileIntegrityError(
                f"Cannot verify '{file_path}': the sandbox did not provide a SHA-256 hash."
            )

        if current_file.sha256 != original_file.sha256:
            raise FileIntegrityError(
                f"Integrity check failed for '{file_path}': "
                "the file has changed since repository inspection."
            )
