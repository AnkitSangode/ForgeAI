import difflib
import hashlib

import pytest

from forgeai.agent.coder_schema import CodeChange
from forgeai.application.repository_clone_service import RepositoryCloneService
from forgeai.core.config import get_settings
from forgeai.execution.file_integrity_verifier import FileIntegrityVerifier
from forgeai.execution.git_change_verifier import GitChangeVerifier
from forgeai.execution.git_state_collector import GitStateCollector
from forgeai.execution.patch_application import PatchApplicationService
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.post_application_verifier import PostApplicationVerifier
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)


@pytest.mark.integration
def test_patch_application_in_real_e2b_sandbox():
    # 1. Initialize the real sandbox provider and application services.
    settings = get_settings()
    provider = E2BSandboxProvider(settings)

    clone_service = RepositoryCloneService(provider)

    patch_service = PatchApplicationService(
        sandbox_provider=provider,
        patch_validator=PatchValidator(),
        integrity_verifier=FileIntegrityVerifier(provider),
        post_application_verifier=PostApplicationVerifier(provider),
        git_state_collector=GitStateCollector(provider),
        git_change_verifier=GitChangeVerifier(),
    )

    session = provider.create(timeout_seconds=300)

    try:
        # 2. Clone a real public repository.
        clone_result = clone_service.clone(
            session=session,
            repository_url="https://github.com/octocat/Hello-World",
        )

        assert clone_result.repository_path == "repository"
        assert len(clone_result.commit_sha) in (40, 64)

        # 3. Find a tracked file using Git.
        result = provider.run_command(
            session=session,
            command="git -C repository ls-files -z",
            timeout_seconds=30,
        )

        assert result.exit_code == 0, result.stderr

        tracked_files = [path for path in result.stdout.split("\x00") if path]

        assert tracked_files, "The cloned repository contains no tracked files."

        # Prefer README.md, otherwise use the first tracked file.
        file_path = next(
            (path for path in tracked_files if path.lower() == "readme.md"),
            tracked_files[0],
        )

        # 4. Read the actual file from E2B.
        sandbox_path = f"repository/{file_path}"

        original_result = provider.read_file(
            session=session,
            file_path=sandbox_path,
        )

        assert original_result.content is not None
        assert original_result.sha256 is not None

        original_content = original_result.content

        # Ensure we are working with a text file.
        assert isinstance(original_content, str)

        # 5. Create a deterministic modification.
        marker = "\nForgeAI E2B integration test modification.\n"

        modified_content = (
            original_content
            + ("" if original_content.endswith("\n") else "\n")
            + marker.lstrip("\n")
        )

        # 6. Generate a real unified diff.
        diff_lines = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            modified_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="\n",
        )

        unified_diff = "".join(diff_lines)

        assert unified_diff

        change = CodeChange(
            file_path=file_path,
            change_type="modify",
            unified_diff=unified_diff,
            explanation=(
                "Append a marker to verify real patch application inside an isolated E2B sandbox."
            ),
        )

        changes = [change]

        # 7. Construct the original repository snapshot.
        repository_context = RepositoryContextResult(
            status="available",
            files=[
                RepositoryFileContext(
                    file_path=file_path,
                    content=original_content,
                    sha256=hashlib.sha256(original_content.encode("utf-8")).hexdigest(),
                )
            ],
            total_bytes=len(original_content.encode("utf-8")),
            skipped_files=[],
            errors=[],
        )

        # 8. Execute the complete patch application pipeline.
        application_result = patch_service.apply(
            session=session,
            changes=changes,
            allowed_paths={file_path},
            repository_context=repository_context,
        )

        # 9. Verify the application result.
        assert application_result.success is True
        assert application_result.changed_files == [file_path]

        # 10. Verify the actual file contents inside E2B.
        final_result = provider.read_file(
            session=session,
            file_path=sandbox_path,
        )

        assert final_result.content == modified_content
        assert final_result.sha256 != original_result.sha256

        # 11. Verify the temporary patch file was cleaned up.
        assert not provider.file_exists(
            session=session,
            file_path=PatchApplicationService.PATCH_FILE_PATH,
        )

        # 12. Verify Git reports exactly the expected modification.
        git_state = GitStateCollector(provider).capture(session)

        assert file_path in git_state.modified_files
        assert file_path not in git_state.untracked_files
        assert file_path not in git_state.deleted_files

        # There should be no other changed files.
        assert git_state.modified_files == frozenset({file_path})
        assert git_state.untracked_files == frozenset()
        assert git_state.deleted_files == frozenset()

    finally:
        if provider.is_running(session):
            provider.terminate(session)
