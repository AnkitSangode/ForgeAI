from unittest.mock import MagicMock

import pytest

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import FileIntegrityError
from forgeai.execution.post_application_verifier import (
    PostApplicationVerifier,
)
from forgeai.execution.sandbox.base import SandboxFileResult
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)


@pytest.fixture
def sandbox_provider():
    return MagicMock()


@pytest.fixture
def verifier(sandbox_provider):
    return PostApplicationVerifier(sandbox_provider)


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def original_file():
    return RepositoryFileContext(
        file_path="src/auth.py",
        content="original content",
        sha256="original_hash",
    )


@pytest.fixture
def repository_context(original_file):
    return RepositoryContextResult(
        status="available",
        files=[original_file],
        total_bytes=len(original_file.content),
        skipped_files=[],
        errors=[],
    )


def make_change(
    change_type: str,
    file_path: str = "src/auth.py",
) -> CodeChange:
    return CodeChange(
        file_path=file_path,
        change_type=change_type,
        unified_diff="--- a/src/auth.py\n+++ b/src/auth.py\n",
        explanation="Update the authentication implementation.",
    )


def test_created_file_exists(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("create", "src/new_file.py")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/new_file.py",
        sha256="created_hash",
    )

    verifier.verify(
        session=session,
        changes=[change],
        repository_context=repository_context,
    )

    sandbox_provider.file_exists.assert_called_once_with(
        session,
        "src/new_file.py",
    )
    sandbox_provider.read_file.assert_called_once_with(
        session,
        "src/new_file.py",
    )


def test_created_file_does_not_exist(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("create", "src/new_file.py")
    sandbox_provider.file_exists.return_value = False

    with pytest.raises(FileIntegrityError, match="does not exist"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )

    sandbox_provider.read_file.assert_not_called()


def test_modified_file_has_different_hash(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("modify")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        sha256="modified_hash",
    )

    verifier.verify(
        session=session,
        changes=[change],
        repository_context=repository_context,
    )

    sandbox_provider.read_file.assert_called_once_with(
        session,
        "src/auth.py",
    )


def test_modified_file_has_original_hash(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("modify")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        sha256="original_hash",
    )

    with pytest.raises(FileIntegrityError, match="was not modified"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )


def test_modified_file_does_not_exist(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("modify")
    sandbox_provider.file_exists.return_value = False

    with pytest.raises(FileIntegrityError, match="is missing"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )

    sandbox_provider.read_file.assert_not_called()


def test_modified_file_has_no_original_snapshot(
    verifier,
    sandbox_provider,
    session,
):
    change = make_change("modify")

    empty_context = RepositoryContextResult(
        status="unavailable",
        files=[],
        total_bytes=0,
        skipped_files=[],
        errors=["Repository snapshot unavailable."],
    )

    with pytest.raises(FileIntegrityError, match="original snapshot missing"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=empty_context,
        )

    sandbox_provider.file_exists.assert_not_called()


def test_deleted_file_does_not_exist(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("delete")
    sandbox_provider.file_exists.return_value = False

    verifier.verify(
        session=session,
        changes=[change],
        repository_context=repository_context,
    )

    sandbox_provider.file_exists.assert_called_once_with(
        session,
        "src/auth.py",
    )

    sandbox_provider.read_file.assert_not_called()


def test_deleted_file_still_exists(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("delete")
    sandbox_provider.file_exists.return_value = True

    with pytest.raises(FileIntegrityError, match="still exists"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )

    sandbox_provider.read_file.assert_not_called()


def test_empty_changes_are_rejected(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    with pytest.raises(FileIntegrityError, match="no code changes"):
        verifier.verify(
            session=session,
            changes=[],
            repository_context=repository_context,
        )

    sandbox_provider.file_exists.assert_not_called()
    sandbox_provider.read_file.assert_not_called()


def test_created_file_without_sha256_is_rejected(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("create", "src/new_file.py")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/new_file.py",
        sha256=None,
    )

    with pytest.raises(FileIntegrityError, match="SHA-256 unavailable"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )


def test_modified_file_without_sha256_is_rejected(
    verifier,
    sandbox_provider,
    session,
    repository_context,
):
    change = make_change("modify")

    sandbox_provider.file_exists.return_value = True
    sandbox_provider.read_file.return_value = SandboxFileResult(
        file_path="src/auth.py",
        sha256=None,
    )

    with pytest.raises(FileIntegrityError, match="SHA-256 unavailable"):
        verifier.verify(
            session=session,
            changes=[change],
            repository_context=repository_context,
        )
