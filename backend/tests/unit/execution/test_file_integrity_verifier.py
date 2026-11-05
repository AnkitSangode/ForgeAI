from unittest.mock import MagicMock

import pytest

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import FileIntegrityError
from forgeai.execution.file_integrity_verifier import FileIntegrityVerifier
from forgeai.execution.sandbox.base import (
    SandboxFileResult,
    SandboxSession,
)
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)


@pytest.fixture
def sandbox_provider():
    return MagicMock()


@pytest.fixture
def session():
    return SandboxSession(
        sandbox_id="test-sandbox",
        _handle=MagicMock(),
    )


@pytest.fixture
def verifier(sandbox_provider):
    return FileIntegrityVerifier(sandbox_provider)


@pytest.fixture
def repository_context():
    return RepositoryContextResult(
        status="available",
        files=[
            RepositoryFileContext(
                file_path="src/auth.py",
                content="original content",
                sha256="a" * 64,
            )
        ],
        total_bytes=16,
        skipped_files=[],
        errors=[],
    )


def make_change(file_path, change_type):
    return CodeChange(
        file_path=file_path,
        change_type=change_type,
        unified_diff="--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1 +1 @@\n-old\n+new",
        explanation="Update the authentication implementation.",
    )


def test_modify_passes_when_hash_matches(verifier, sandbox_provider, session, repository_context):
    change = make_change("src/auth.py", "modify")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        content="original content",
        sha256="a" * 64,
    )

    verifier.verify(session, [change], repository_context)

    sandbox_provider.read_file.assert_called_once_with(session, "src/auth.py")


def test_modify_fails_when_hash_differs(verifier, sandbox_provider, session, repository_context):
    change = make_change("src/auth.py", "modify")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        content="changed content",
        sha256="b" * 64,
    )

    with pytest.raises(FileIntegrityError, match="changed since"):
        verifier.verify(session, [change], repository_context)


def test_modify_fails_when_file_is_missing(verifier, sandbox_provider, session, repository_context):
    change = make_change("src/auth.py", "modify")
    sandbox_provider.file_exists.return_value = False

    with pytest.raises(FileIntegrityError, match="no longer exists"):
        verifier.verify(session, [change], repository_context)


def test_modify_fails_without_original_snapshot(verifier, sandbox_provider, session):
    change = make_change("src/unknown.py", "modify")

    context = RepositoryContextResult(
        status="available",
        files=[],
        total_bytes=0,
        skipped_files=[],
        errors=[],
    )

    with pytest.raises(FileIntegrityError, match="no original"):
        verifier.verify(session, [change], context)

    sandbox_provider.read_file.assert_not_called()


def test_create_passes_when_file_does_not_exist(
    verifier, sandbox_provider, session, repository_context
):
    change = make_change("src/new_file.py", "create")
    sandbox_provider.file_exists.return_value = False

    verifier.verify(session, [change], repository_context)

    sandbox_provider.read_file.assert_not_called()


def test_create_fails_when_file_already_exists(
    verifier, sandbox_provider, session, repository_context
):
    change = make_change("src/new_file.py", "create")
    sandbox_provider.file_exists.return_value = True

    with pytest.raises(FileIntegrityError, match="already exists"):
        verifier.verify(session, [change], repository_context)


def test_delete_passes_when_hash_matches(verifier, sandbox_provider, session, repository_context):
    change = make_change("src/auth.py", "delete")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        content="original content",
        sha256="a" * 64,
    )

    verifier.verify(session, [change], repository_context)
