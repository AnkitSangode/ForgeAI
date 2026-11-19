from types import SimpleNamespace
from unittest.mock import MagicMock

from forgeai.agent.execution_nodes import (
    create_approved_patch_execution_node,
    create_execution_record_node,
)


def test_execution_record_requires_verified_human_approval():
    node = create_execution_record_node(MagicMock())

    result = node({
        "approval_id": "approval",
        "task_id": "task",
        "agent_run_id": "run",
        "patch_sha256": "a" * 64,
        "human_approval_status": "pending",
    })

    assert result["status"] == "failed"
    assert "human approval" in result["error"].lower()


def test_execution_record_persists_and_returns_execution_id():
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__enter__.return_value = session
    execution = SimpleNamespace(
        execution_id="execution-1",
        status=SimpleNamespace(value="pending"),
    )
    service = MagicMock()
    service.create_execution.return_value = execution

    # Patch service construction at its import site.
    import forgeai.agent.execution_nodes as module
    original = module.PatchExecutionService
    module.PatchExecutionService = MagicMock(return_value=service)
    try:
        result = create_execution_record_node(session_factory)({
            "approval_id": "approval",
            "task_id": "task",
            "agent_run_id": "run",
            "patch_sha256": "a" * 64,
            "human_approval_status": "approved",
        })
    finally:
        module.PatchExecutionService = original

    assert result["execution_id"] == "execution-1"
    assert result["execution_status"] == "pending"
    assert result["status"] == "execution_pending"


def test_worker_is_not_called_without_verified_approval():
    session_factory = MagicMock()
    worker_factory = MagicMock()
    node = create_approved_patch_execution_node(
        session_factory=session_factory,
        worker_factory=worker_factory,
    )

    result = node({
        "execution_id": "execution-1",
        "sandbox_id": "sandbox-1",
        "patch_sha256": "a" * 64,
        "code_changes": {"changes": []},
        "repository_context_files": [{"file_path": "a.py", "content": "", "sha256": "b"}],
        "human_approval_status": "pending",
    })

    assert result["status"] == "failed"
    worker_factory.assert_not_called()
