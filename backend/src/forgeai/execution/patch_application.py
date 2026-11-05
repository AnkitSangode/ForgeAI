from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.appication_result import PatchApplicationResult
from forgeai.execution.file_integrity_verifier import (
    FileIntegrityVerifier,
)
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
)


class PatchApplicationService:
    """Coordinates safe patch application inside an isolated sandbox."""

    PATCH_FILE_PATH = ".forgeai-current.patch"

    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        patch_validator: PatchValidator,
        integrity_verifier: FileIntegrityVerifier,
    ) -> None:
        self.sandbox_provider = sandbox_provider
        self.patch_validator = patch_validator
        self.integrity_verifier = integrity_verifier

    def apply(
        self,
        session: SandboxSession,
        changes: list[CodeChange],
        allowed_paths: set[str],
        repository_context: RepositoryContextResult,
    ) -> PatchApplicationResult:
        """Validate, verify, and apply approved code changes."""
        raise NotImplementedError
