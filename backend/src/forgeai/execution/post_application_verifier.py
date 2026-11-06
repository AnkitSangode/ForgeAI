
from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import FileIntegrityError
from forgeai.execution.repository_paths import resolve_repository_file_path
from forgeai.execution.sandbox.base import (
    SandboxProvider,
    SandboxSession,
)
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
)


class PostApplicationVerifier:
    """Verifies the repository state after patch application."""

    def __init__(self, sandbox_provider: SandboxProvider) -> None:
        self.sandbox_provider = sandbox_provider

    def verify(
        self,
        session: SandboxSession,
        changes: list[CodeChange],
        repository_context: RepositoryContextResult,
    ) -> None:
        """Verify that every proposed change was applied as expected."""

        if not changes:
            raise FileIntegrityError(
                "Cannot verify application: no code changes were provided."
            )

        original_files = {
            file.file_path: file for file in repository_context.files
        }

        for change in changes:
            try:
                sandbox_path = resolve_repository_file_path(change.file_path)
            except ValueError as exc:
                raise FileIntegrityError(
                    f"Invalid repository file path '{change.file_path}'."
                ) from exc

            if change.change_type == "create":
                self._verify_created_file(
                    session=session,
                    file_path=change.file_path,
                    sandbox_path=sandbox_path,
                )

            elif change.change_type == "modify":
                self._verify_modified_file(
                    session=session,
                    file_path=change.file_path,
                    sandbox_path=sandbox_path,
                    original_files=original_files,
                )

            elif change.change_type == "delete":
                self._verify_deleted_file(
                    session=session,
                    file_path=change.file_path,
                    sandbox_path=sandbox_path,
                )

            else:
                raise FileIntegrityError(
                    f"Unsupported change type: {change.change_type}"
                )

    def _verify_created_file(
        self,
        session: SandboxSession,
        file_path: str,
        sandbox_path: str,
    ) -> None:
        if not self.sandbox_provider.file_exists(session, sandbox_path):
            raise FileIntegrityError(
                f"Patch application failed: created file '{file_path}' does not exist."
            )

        result = self.sandbox_provider.read_file(session, sandbox_path)

        if result.sha256 is None:
            raise FileIntegrityError(
                f"Cannot verify created file '{file_path}': SHA-256 unavailable."
            )

    def _verify_modified_file(
        self,
        session: SandboxSession,
        file_path: str,
        sandbox_path: str,
        original_files: dict,
    ) -> None:
        original_file = original_files.get(file_path)

        if original_file is None:
            raise FileIntegrityError(
                f"Cannot verify modified file '{file_path}': original snapshot missing."
            )

        if not self.sandbox_provider.file_exists(session, sandbox_path):
            raise FileIntegrityError(
                f"Patch application failed: modified file '{file_path}' is missing."
            )

        result = self.sandbox_provider.read_file(session, sandbox_path)

        if result.sha256 is None:
            raise FileIntegrityError(
                f"Cannot verify modified file '{file_path}': SHA-256 unavailable."
            )

        if result.sha256 == original_file.sha256:
            raise FileIntegrityError(
                f"Patch application failed: '{file_path}' was not modified."
            )

    def _verify_deleted_file(
        self,
        session: SandboxSession,
        file_path: str,
        sandbox_path: str,
    ) -> None:
        if self.sandbox_provider.file_exists(session, sandbox_path):
            raise FileIntegrityError(
                f"Patch application failed: deleted file '{file_path}' still exists."
            )
