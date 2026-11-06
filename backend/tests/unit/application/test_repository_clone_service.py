
from unittest.mock import Mock

import pytest

from forgeai.application.repository_clone_service import RepositoryCloneService
from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.sandbox.base import CommandExecutionResult, SandboxSession


@pytest.fixture
def provider():
    return Mock()


@pytest.fixture
def service(provider):
    return RepositoryCloneService(provider)


@pytest.fixture
def session():
    return SandboxSession(
        sandbox_id="sandbox-test",
        _handle=object(),
    )


def test_validate_github_url():
    result = RepositoryCloneService._validate_repository_url(
        "https://github.com/owner/project"
    )

    assert result == "https://github.com/owner/project.git"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/project",
        "https://example.com/owner/project",
        "https://github.com/owner/project/extra",
        "https://user:password@github.com/owner/project",
        "https://github.com/owner/project?token=secret",
        "https://github.com.evil.com/owner/project",
        "https://github.com/owner/project#fragment",
    ],
)
def test_rejects_invalid_repository_urls(url):
    with pytest.raises(ValueError):
        RepositoryCloneService._validate_repository_url(url)


def test_clone_success(service, provider, session):
    provider.file_exists.return_value = False

    provider.run_command.side_effect = [
        CommandExecutionResult(
            command="git clone",
            exit_code=0,
            stdout="",
            stderr="",
        ),
        CommandExecutionResult(
            command="git -C repository rev-parse HEAD",
            exit_code=0,
            stdout="abc123\n",
            stderr="",
        ),
    ]

    result = service.clone(
        session,
        "https://github.com/owner/project",
    )

    assert result.repository_name == "project"
    assert result.repository_path == "repository"
    assert result.commit_sha == "abc123"

    assert provider.run_command.call_count == 2


def test_clone_rejects_existing_destination(service, provider, session):
    provider.file_exists.return_value = True

    with pytest.raises(PatchApplicationError):
        service.clone(
            session,
            "https://github.com/owner/project",
        )

    provider.run_command.assert_not_called()


def test_clone_failure(service, provider, session):
    provider.file_exists.return_value = False

    provider.run_command.return_value = CommandExecutionResult(
        command="git clone",
        exit_code=128,
        stdout="",
        stderr="Repository not found",
    )

    with pytest.raises(PatchApplicationError):
        service.clone(
            session,
            "https://github.com/owner/project",
        )
