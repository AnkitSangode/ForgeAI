from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from forgeai.agent.nodes import create_patch_preparation_node
from forgeai.application.patch_preparation_service import (
    PatchPreparationError,
    PatchPreparationResult,
)


@pytest.fixture
def preparation_service():
    service = MagicMock()
    service.prepare.return_value = PatchPreparationResult(
        patch="--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1 +1 @@\n-old\n+new\n",
        patch_sha256=sha256(
            b"--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1 +1 @@\n-old\n+new\n"
        ).hexdigest(),
        changed_files=["src/auth.py"],
        summary="Fix authentication validation.",
        tests_to_run=["uv run pytest tests/unit"],
        risks=["Existing sessions may require reauthentication."],
    )
    return service


@pytest.fixture
def node(preparation_service):
    return create_patch_preparation_node(preparation_service)


@pytest.fixture
def valid_state():
    return {
        "status": "review_completed",
        "code_changes": {
            "summary": "Fix authentication validation.",
            "changes": [
                {
                    "file_path": "src/auth.py",
                    "change_type": "modify",
                    "unified_diff": (
                        "--- a/src/auth.py\n+++ b/src/auth.py\n"
                        "@@ -1 +1 @@\n-old\n+new\n"
                    ),
                    "explanation": "Correctly validate the authentication result.",
                }
            ],
            "tests_to_run": ["uv run pytest tests/unit"],
            "risks": [],
        },
        "repository_context_files": [
            {
                "file_path": "src/auth.py",
                "content": "old",
                "sha256": sha256(b"old").hexdigest(),
            }
        ],
        "repository_context_status": "available",
        "repository_context_bytes": 3,
        "repository_context_skipped_files": [],
        "repository_context_errors": [],
        "authorized_new_paths": [],
    }


def test_patch_preparation_node_stores_prepared_patch(
    node, preparation_service, valid_state
):
    result = node(valid_state)

    assert result["status"] == "patch_prepared"
    assert result["patch"].startswith("--- a/src/auth.py")
    assert len(result["patch_sha256"]) == 64
    assert result["changed_files"] == ["src/auth.py"]
    assert result["allowed_paths"] == ["src/auth.py"]
    assert result["patch_summary"] == "Fix authentication validation."
    assert result["tests_to_run"] == ["uv run pytest tests/unit"]
    assert result["patch_risks"] == ["Existing sessions may require reauthentication."]
    assert result["error"] == ""

    preparation_service.prepare.assert_called_once()
    kwargs = preparation_service.prepare.call_args.kwargs
    assert kwargs["authorized_new_paths"] == set()
    assert kwargs["repository_context"].files[0].file_path == "src/auth.py"


def test_patch_preparation_node_skips_failed_workflow(
    node, preparation_service, valid_state
):
    valid_state["status"] = "failed"

    assert node(valid_state) == {}
    preparation_service.prepare.assert_not_called()


def test_patch_preparation_node_fails_when_coder_output_is_missing(
    node, preparation_service, valid_state
):
    valid_state.pop("code_changes")

    result = node(valid_state)

    assert result["status"] == "failed"
    assert "no code changes" in result["error"].lower()
    preparation_service.prepare.assert_not_called()


def test_patch_preparation_node_fails_when_repository_context_is_missing(
    node, preparation_service, valid_state
):
    valid_state["repository_context_files"] = []

    result = node(valid_state)

    assert result["status"] == "failed"
    assert "repository context" in result["error"].lower()
    preparation_service.prepare.assert_not_called()


def test_patch_preparation_node_passes_explicit_new_path_authorization(
    node, preparation_service, valid_state
):
    valid_state["authorized_new_paths"] = ["src/new_module.py"]

    result = node(valid_state)

    assert result["allowed_paths"] == ["src/auth.py", "src/new_module.py"]
    assert preparation_service.prepare.call_args.kwargs["authorized_new_paths"] == {
        "src/new_module.py"
    }


def test_patch_preparation_node_handles_service_validation_error(
    node, preparation_service, valid_state
):
    preparation_service.prepare.side_effect = PatchPreparationError(
        "Cannot modify an uninspected file."
    )

    result = node(valid_state)

    assert result["status"] == "failed"
    assert "uninspected file" in result["error"].lower()


def test_patch_preparation_node_rejects_invalid_coder_output(
    node, preparation_service, valid_state
):
    valid_state["code_changes"] = {"summary": "invalid"}

    result = node(valid_state)

    assert result["status"] == "failed"
    preparation_service.prepare.assert_not_called()
