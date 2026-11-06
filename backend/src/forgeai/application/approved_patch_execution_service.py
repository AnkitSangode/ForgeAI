from forgeai.agent.coder_schema import CodeChange
from forgeai.application.patch_approval_service import PatchApprovalService
from forgeai.execution.application_result import PatchApplicationResult
from forgeai.execution.patch_application import PatchApplicationService
from forgeai.execution.patch_fingerprint import generate_patch_fingerprint
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.sandbox.base import SandboxSession
from forgeai.services.repository_context_result import RepositoryContextResult


class ApprovedPatchExecutionService:
    def __init__(
        self,
        approval_service: PatchApprovalService,
        patch_application_service: PatchApplicationService,
        patch_validator: PatchValidator,
    ) -> None:
        self.approval_service = approval_service
        self.patch_application_service = patch_application_service
        self.patch_validator = patch_validator

    def execute(
        self,
        approval_id: str,
        task_id: str,
        session: SandboxSession,
        changes: list[CodeChange],
        allowed_paths: set[str],
        repository_context: RepositoryContextResult,
    ) -> PatchApplicationResult:

        # 1. Validate the patch before consuming approval.
        self.patch_validator.validate(
            changes=changes,
            allowed_paths=allowed_paths,
        )

        # 2. Generate a deterministic fingerprint.
        patch_sha256 = generate_patch_fingerprint(changes)

        # 3. Consume the exact approval.
        self.approval_service.consume_approval(
            approval_id=approval_id,
            task_id=task_id,
            patch_sha256=patch_sha256,
        )

        # 4. Execute only after approval consumption succeeds.
        return self.patch_application_service.apply(
            session=session,
            changes=changes,
            allowed_paths=allowed_paths,
            repository_context=repository_context,
        )