import logging

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.application_result import PatchApplicationResult
from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.file_integrity_verifier import (
    FileIntegrityVerifier,
)
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.post_application_verifier import (
    PostApplicationVerifier,
)
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession
from forgeai.services.repository_context_result import RepositoryContextResult

logger = logging.getLogger(__name__)


class PatchApplicationService:
    """Coordinates safe patch application inside an isolated sandbox."""

    PATCH_FILE_PATH = ".forgeai-current.patch"
    COMMAND_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        patch_validator: PatchValidator,
        integrity_verifier: FileIntegrityVerifier,
        post_application_verifier: PostApplicationVerifier,
    ) -> None:
        self.sandbox_provider = sandbox_provider
        self.patch_validator = patch_validator
        self.integrity_verifier = integrity_verifier
        self.post_application_verifier = post_application_verifier

    def apply(
        self,
        session: SandboxSession,
        changes: list[CodeChange],
        allowed_paths: set[str],
        repository_context: RepositoryContextResult,
    ) -> PatchApplicationResult:
        """Validate, apply, and verify a patch inside the sandbox."""

        changed_files = [change.file_path for change in changes]

        try:
            # 1. Validate patch structure and authorized paths.
            self.patch_validator.validate(
                changes=changes,
                allowed_paths=allowed_paths,
            )

            # 2. Verify original files haven't changed.
            self.integrity_verifier.verify(
                session=session,
                changes=changes,
                repository_context=repository_context,
            )

            # 3. Generate combined unified diff.
            patch = self._build_patch(changes)

            # 4. Verify Git repository.
            self._ensure_git_repository(session)

            # 5. Write patch into sandbox.
            self._write_patch(session, patch)

            # 6. Check whether Git can apply it.
            self._check_patch(session)

            # 7. Apply patch.
            self._apply_patch(session)

            # 8. Verify resulting repository state.
            self.post_application_verifier.verify(
                session=session,
                changes=changes,
                repository_context=repository_context,
            )

            return PatchApplicationResult(
                success=True,
                changed_files=changed_files,
                message="Patch applied and verified successfully.",
            )

        finally:
            self._cleanup_patch_file(session)

    def _cleanup_patch_file(self, session: SandboxSession) -> None:
        """Best-effort cleanup of the temporary patch file."""

        try:
            if self.sandbox_provider.file_exists(
                session,
                self.PATCH_FILE_PATH,
            ):
                self.sandbox_provider.delete_file(
                    session,
                    self.PATCH_FILE_PATH,
                )
        except (FileNotFoundError, PermissionError, OSError) as exc:
            logger.warning(
                "Failed to clean up temporary patch file '%s': %s",
                self.PATCH_FILE_PATH,
                exc,
                exc_info=True,
            )

    @staticmethod
    def _build_patch(changes: list[CodeChange]) -> str:
        """Combine individual unified diffs into one patch."""

        if not changes:
            raise PatchApplicationError("Cannot build a patch without code changes.")

        patch_parts = [change.unified_diff.rstrip("\n") for change in changes]

        return "\n".join(patch_parts) + "\n"

    def _ensure_git_repository(self, session: SandboxSession) -> None:
        """Ensure the sandbox workspace contains a Git repository."""

        result = self.sandbox_provider.run_command(
            session=session,
            command="git rev-parse --is-inside-work-tree",
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0 or result.stdout.strip() != "true":
            raise PatchApplicationError("Sandbox workspace is not a valid Git repository.")

    def _write_patch(
        self,
        session: SandboxSession,
        patch: str,
    ) -> None:
        """Write the generated patch into the sandbox."""

        try:
            self.sandbox_provider.create_file(
                session=session,
                file_path=self.PATCH_FILE_PATH,
                content=patch,
            )
        except FileExistsError as exc:
            raise PatchApplicationError("A patch file already exists in the sandbox.") from exc
        except Exception as exc:
            raise PatchApplicationError("Failed to write the patch into the sandbox.") from exc

    def _check_patch(self, session: SandboxSession) -> None:
        """Check whether Git can apply the patch without modifying files."""

        result = self.sandbox_provider.run_command(
            session=session,
            command=f"git apply --check {self.PATCH_FILE_PATH}",
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError(f"Patch validation by Git failed: {result.stderr}")

    def _apply_patch(self, session: SandboxSession) -> None:
        """Apply the validated patch inside the sandbox."""

        result = self.sandbox_provider.run_command(
            session=session,
            command=f"git apply {self.PATCH_FILE_PATH}",
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError(f"Git failed to apply the patch: {result.stderr}")
