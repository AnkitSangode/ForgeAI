
import logging

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.application_result import PatchApplicationResult
from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.file_integrity_verifier import FileIntegrityVerifier
from forgeai.execution.git_change_verifier import GitChangeVerifier
from forgeai.execution.git_state_collector import GitStateCollector
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.post_application_verifier import PostApplicationVerifier
from forgeai.execution.repository_paths import REPOSITORY_ROOT
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession
from forgeai.services.repository_context_result import RepositoryContextResult

logger = logging.getLogger(__name__)


class PatchApplicationService:
    """Coordinates safe patch application inside an isolated sandbox."""

    # The patch is deliberately stored outside the cloned repository.
    PATCH_FILE_PATH = ".forgeai-current.patch"

    # Git runs from repository/, so the patch is one directory above.
    GIT_PATCH_FILE_PATH = f"../{PATCH_FILE_PATH}"

    COMMAND_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        patch_validator: PatchValidator,
        integrity_verifier: FileIntegrityVerifier,
        post_application_verifier: PostApplicationVerifier,
        git_state_collector: GitStateCollector,
        git_change_verifier: GitChangeVerifier,
    ) -> None:
        self.sandbox_provider = sandbox_provider
        self.patch_validator = patch_validator
        self.integrity_verifier = integrity_verifier
        self.post_application_verifier = post_application_verifier
        self.git_state_collector = git_state_collector
        self.git_change_verifier = git_change_verifier

    def apply(
        self,
        session: SandboxSession,
        changes: list[CodeChange],
        allowed_paths: set[str],
        repository_context: RepositoryContextResult,
    ) -> PatchApplicationResult:
        """Validate, apply, and verify a patch inside the sandbox."""

        changed_files = [change.file_path for change in changes]
        patch_cleanup_completed = False

        try:
            # 1. Validate the proposed changes.
            self.patch_validator.validate(
                changes=changes,
                allowed_paths=allowed_paths,
            )

            # 2. Verify original files have not changed since inspection.
            self.integrity_verifier.verify(
                session=session,
                changes=changes,
                repository_context=repository_context,
            )

            # 3. Ensure the cloned repository is available.
            self._ensure_git_repository(session)

            # 4. Capture the repository state before applying the patch.
            baseline_state = self.git_state_collector.capture(session)

            # 5. Build and write the patch outside the repository.
            patch = self._build_patch(changes)
            self._write_patch(session, patch)

            # 6. Ask Git to validate the patch without applying it.
            self._check_patch(session)

            # 7. Apply the patch to the cloned repository.
            self._apply_patch(session)

            # 8. Verify the resulting files.
            self.post_application_verifier.verify(
                session=session,
                changes=changes,
                repository_context=repository_context,
            )

            # 9. Clean up the temporary patch file.
            self._cleanup_patch_file(session, strict=True)
            patch_cleanup_completed = True

            # 10. Capture the repository state after application.
            final_state = self.git_state_collector.capture(session)

            # 11. Verify that only authorized files changed.
            self.git_change_verifier.verify(
                baseline=baseline_state,
                final_state=final_state,
                expected_changes=changes,
            )

            return PatchApplicationResult(
                success=True,
                changed_files=changed_files,
                message="Patch applied and verified successfully.",
            )

        finally:
            # Retry cleanup if execution failed before successful cleanup.
            if not patch_cleanup_completed:
                self._cleanup_patch_file(session)

    def _cleanup_patch_file(
        self,
        session: SandboxSession,
        strict: bool = False,
    ) -> None:
        """Remove the temporary patch file.

        Strict mode prevents successful execution from being reported
        when cleanup fails. The finally block can still retry cleanup.
        """

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
            if strict:
                raise PatchApplicationError(
                    "Failed to clean up the temporary patch file."
                ) from exc

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
            raise PatchApplicationError(
                "Cannot build a patch without code changes."
            )

        patch_parts = [
            change.unified_diff.rstrip("\n")
            for change in changes
        ]

        return "\n".join(patch_parts) + "\n"

    def _ensure_git_repository(
        self,
        session: SandboxSession,
    ) -> None:
        """Ensure the cloned repository exists inside the sandbox."""

        result = self.sandbox_provider.run_command(
            session=session,
            command=(
                f"git -C {REPOSITORY_ROOT} "
                "rev-parse --is-inside-work-tree"
            ),
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0 or result.stdout.strip() != "true":
            raise PatchApplicationError(
                "Sandbox workspace does not contain a valid Git repository."
            )

    def _write_patch(
        self,
        session: SandboxSession,
        patch: str,
    ) -> None:
        """Write the generated patch into the sandbox workspace."""

        try:
            self.sandbox_provider.create_file(
                session=session,
                file_path=self.PATCH_FILE_PATH,
                content=patch,
            )

        except FileExistsError as exc:
            raise PatchApplicationError(
                "A patch file already exists in the sandbox."
            ) from exc

        except Exception as exc:
            raise PatchApplicationError(
                "Failed to write the patch into the sandbox."
            ) from exc

    def _check_patch(
        self,
        session: SandboxSession,
    ) -> None:
        """Check whether Git can apply the patch without modifying files."""

        result = self.sandbox_provider.run_command(
            session=session,
            command=(
                f"git -C {REPOSITORY_ROOT} "
                f"apply --check {self.GIT_PATCH_FILE_PATH}"
            ),
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError(
                f"Patch validation by Git failed: {result.stderr}"
            )

    def _apply_patch(
        self,
        session: SandboxSession,
    ) -> None:
        """Apply the validated patch inside the cloned repository."""

        result = self.sandbox_provider.run_command(
            session=session,
            command=(
                f"git -C {REPOSITORY_ROOT} "
                f"apply {self.GIT_PATCH_FILE_PATH}"
            ),
            timeout_seconds=self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError(
                f"Git failed to apply the patch: {result.stderr}"
            )
