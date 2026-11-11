
import hashlib
from dataclasses import dataclass

from forgeai.agent.coder_schema import CoderResponse
from forgeai.execution.exceptions import PatchValidationError
from forgeai.execution.patch_builder import PatchBuilder
from forgeai.execution.patch_validator import PatchValidator
from forgeai.services.repository_context_result import RepositoryContextResult


class PatchPreparationError(Exception):
    """Raised when a proposed patch cannot be safely prepared."""


@dataclass(frozen=True)
class PatchPreparationResult:
    """Contains a validated patch ready for human approval."""

    patch: str
    patch_sha256: str
    changed_files: list[str]
    summary: str
    tests_to_run: list[str]
    risks: list[str]


class PatchPreparationService:
    """Validates and fingerprints proposed repository changes."""

    def __init__(self, patch_validator: PatchValidator) -> None:
        self.patch_validator = patch_validator

    def prepare(
        self,
        code_response: CoderResponse,
        repository_context: RepositoryContextResult,
        authorized_new_paths: set[str] | None = None,
    ) -> PatchPreparationResult:
        """Prepare a patch without applying it or modifying the repository."""

        if repository_context.status == "unavailable":
            raise PatchPreparationError(
                "Cannot prepare a patch without repository context."
            )

        authorized_new_paths = authorized_new_paths or set()

        # Collect files included in the original repository snapshot.
        inspected_paths = {
            file.file_path for file in repository_context.files
        }

        # Enforce operation-specific authorization.
        for change in code_response.changes:
            if change.change_type in {"modify", "delete"}:
                if change.file_path not in inspected_paths:
                    raise PatchPreparationError(
                        f"Cannot {change.change_type} "
                        f"'{change.file_path}': file was not inspected."
                    )

            elif change.change_type == "create":
                if change.file_path not in authorized_new_paths:
                    raise PatchPreparationError(
                        f"Cannot create '{change.file_path}': "
                        "path has not been explicitly authorized."
                    )

                if change.file_path in inspected_paths:
                    raise PatchPreparationError(
                        f"Cannot create '{change.file_path}': "
                        "path already exists in the inspected repository."
                    )

        # Combine inspected and explicitly authorized paths.
        allowed_paths = inspected_paths | authorized_new_paths

        # Perform structural and path validation.
        try:
            self.patch_validator.validate(
                changes=code_response.changes,
                allowed_paths=allowed_paths,
            )
        except PatchValidationError as exc:
            raise PatchPreparationError(
                f"Patch validation failed: {exc}"
            ) from exc

        # Build the exact patch that execution will later use.
        patch = PatchBuilder.build(code_response.changes)

        # Fingerprint the exact UTF-8 patch content.
        patch_sha256 = hashlib.sha256(
            patch.encode("utf-8")
        ).hexdigest()

        return PatchPreparationResult(
            patch=patch,
            patch_sha256=patch_sha256,
            changed_files=[
                change.file_path for change in code_response.changes
            ],
            summary=code_response.summary,
            tests_to_run=code_response.tests_to_run,
            risks=code_response.risks,
        )
