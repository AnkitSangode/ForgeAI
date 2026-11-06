
import pytest

from forgeai.application.repository_clone_service import RepositoryCloneService
from forgeai.core.config import get_settings
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider


@pytest.mark.integration
def test_clone_public_github_repository():
    settings = get_settings()

    provider = E2BSandboxProvider(settings)
    clone_service = RepositoryCloneService(provider)

    session = provider.create(timeout_seconds=300)

    try:
        result = clone_service.clone(
            session=session,
            repository_url="https://github.com/octocat/Hello-World",
        )

        assert result.repository_name == "Hello-World"
        assert result.repository_path == "repository"
        assert len(result.commit_sha) in (40, 64)

        git_result = provider.run_command(
            session=session,
            command="git -C repository rev-parse --is-inside-work-tree",
            timeout_seconds=30,
        )

        assert git_result.exit_code == 0
        assert git_result.stdout.strip() == "true"

    finally:
        if provider.is_running(session):
            provider.terminate(session)
