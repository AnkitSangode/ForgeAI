
import hashlib
from unittest.mock import MagicMock

import pytest

from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.application.patch_preparation_service import (
    PatchPreparationError,
    PatchPreparationService,
)
from forgeai.execution.exceptions import PatchValidationError
from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)


@pytest.fixture
def patch_validator():
    return MagicMock()


@pytest.fixture
def service(patch_validator):
    return PatchPreparationService(
        patch_validator=patch_validator,
    )


@pytest.fixture
def repository_context():
    return RepositoryContextResult(
        status="available",
        files=[
            RepositoryFileContext(
                file_path="src/app.py",
                content="print('old')\n",
                sha256="original-hash",
            ),
            RepositoryFileContext(
                file_path="src/config.py",
                content="DEBUG = False\n",
                sha256="config-hash",
            ),
        ],
        total_bytes=100,
        skipped_files=[],
        errors=[],
    )


@pytest.fixture
def modify_change():
    return CodeChange(
        file_path="src/app.py",
        change_type="modify",
        unified_diff=(
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1 @@\n"
            "-print('old')\n"
            "+print('new')\n"
        ),
        explanation="Update application output.",
    )


@pytest.fixture
def create_change():
    return CodeChange(
        file_path="src/new_module.py",
        change_type="create",
        unified_diff=(
            "--- /dev/null\n"
            "+++ b/src/new_module.py\n"
            "@@ -0,0 +1 @@\n"
            "+print('created')\n"
        ),
        explanation="Create a new application module.",
    )


@pytest.fixture
def delete_change():
    return CodeChange(
        file_path="src/config.py",
        change_type="delete",
        unified_diff=(
            "--- a/src/config.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-DEBUG = False\n"
        ),
        explanation="Remove obsolete configuration.",
    )


def make_coder_response(*changes):
    return CoderResponse(
        summary="Update the application implementation.",
        changes=list(changes),
        tests_to_run=["tests/test_app.py"],
        risks=["Existing behavior may change."],
    )


def test_prepare_modify_inspected_file(
    service,
    patch_validator,
    repository_context,
    modify_change,
):
    response = make_coder_response(modify_change)

    result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    assert result.changed_files == ["src/app.py"]
    assert result.patch == modify_change.unified_diff
    assert len(result.patch_sha256) == 64

    patch_validator.validate.assert_called_once_with(
        changes=response.changes,
        allowed_paths={"src/app.py", "src/config.py"},
    )


def test_prepare_delete_inspected_file(
    service,
    patch_validator,
    repository_context,
    delete_change,
):
    response = make_coder_response(delete_change)

    result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    assert result.changed_files == ["src/config.py"]

    patch_validator.validate.assert_called_once_with(
        changes=response.changes,
        allowed_paths={"src/app.py", "src/config.py"},
    )


def test_prepare_explicitly_authorized_new_file(
    service,
    patch_validator,
    repository_context,
    create_change,
):
    response = make_coder_response(create_change)

    result = service.prepare(
        code_response=response,
        repository_context=repository_context,
        authorized_new_paths={"src/new_module.py"},
    )

    assert result.changed_files == ["src/new_module.py"]

    patch_validator.validate.assert_called_once_with(
        changes=response.changes,
        allowed_paths={
            "src/app.py",
            "src/config.py",
            "src/new_module.py",
        },
    )


def test_reject_unauthorized_new_file(
    service,
    patch_validator,
    repository_context,
    create_change,
):
    response = make_coder_response(create_change)

    with pytest.raises(
        PatchPreparationError,
        match="not been explicitly authorized",
    ):
        service.prepare(
            code_response=response,
            repository_context=repository_context,
        )

    patch_validator.validate.assert_not_called()


@pytest.mark.parametrize("change_type", ["modify", "delete"])
def test_reject_uninspected_existing_file(
    service,
    repository_context,
    change_type,
):
    change = CodeChange(
        file_path="src/unknown.py",
        change_type=change_type,
        unified_diff=(
            "--- a/src/unknown.py\n"
            "+++ b/src/unknown.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        ),
        explanation="Update an uninspected file.",
    )

    response = make_coder_response(change)

    with pytest.raises(
        PatchPreparationError,
        match="file was not inspected",
    ):
        service.prepare(
            code_response=response,
            repository_context=repository_context,
        )


def test_reject_creation_of_existing_file(
    service,
    repository_context,
):
    change = CodeChange(
        file_path="src/app.py",
        change_type="create",
        unified_diff=(
            "--- /dev/null\n"
            "+++ b/src/app.py\n"
            "@@ -0,0 +1 @@\n"
            "+print('new')\n"
        ),
        explanation="Attempt to create an existing file.",
    )

    response = make_coder_response(change)

    with pytest.raises(
        PatchPreparationError,
        match="already exists",
    ):
        service.prepare(
            code_response=response,
            repository_context=repository_context,
            authorized_new_paths={"src/app.py"},
        )


def test_reject_unavailable_repository_context(
    service,
    modify_change,
):
    unavailable_context = RepositoryContextResult(
        status="unavailable",
        files=[],
        total_bytes=0,
        skipped_files=[],
        errors=["Repository inspection failed."],
    )

    response = make_coder_response(modify_change)

    with pytest.raises(
        PatchPreparationError,
        match="without repository context",
    ):
        service.prepare(
            code_response=response,
            repository_context=unavailable_context,
        )


def test_reject_invalid_diff_headers(
    service,
    repository_context,
    modify_change,
    patch_validator,
):
    patch_validator.validate.side_effect = PatchValidationError(
        "Diff headers do not match the requested operation."
    )

    response = make_coder_response(modify_change)

    with pytest.raises(
        PatchPreparationError,
        match="Patch validation failed",
    ):
        service.prepare(
            code_response=response,
            repository_context=repository_context,
        )


def test_same_patch_generates_same_sha256(
    service,
    repository_context,
    modify_change,
):
    response = make_coder_response(modify_change)

    first_result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    second_result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    assert first_result.patch_sha256 == second_result.patch_sha256


def test_different_patch_generates_different_sha256(
    service,
    repository_context,
    modify_change,
):
    first_response = make_coder_response(modify_change)

    first_result = service.prepare(
        code_response=first_response,
        repository_context=repository_context,
    )

    different_change = CodeChange(
        file_path="src/app.py",
        change_type="modify",
        unified_diff=(
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1 @@\n"
            "-print('old')\n"
            "+print('different')\n"
        ),
        explanation="Change application output differently.",
    )

    second_result = service.prepare(
        code_response=make_coder_response(different_change),
        repository_context=repository_context,
    )

    assert first_result.patch_sha256 != second_result.patch_sha256


def test_patch_fingerprint_matches_exact_patch(
    service,
    repository_context,
    modify_change,
):
    response = make_coder_response(modify_change)

    result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    expected_hash = hashlib.sha256(
        result.patch.encode("utf-8")
    ).hexdigest()

    assert result.patch_sha256 == expected_hash


def test_result_preserves_coder_metadata(
    service,
    repository_context,
    modify_change,
):
    response = make_coder_response(modify_change)

    result = service.prepare(
        code_response=response,
        repository_context=repository_context,
    )

    assert result.summary == response.summary
    assert result.tests_to_run == response.tests_to_run
    assert result.risks == response.risks
