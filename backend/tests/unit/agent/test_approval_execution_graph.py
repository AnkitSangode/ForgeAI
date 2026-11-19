from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

import forgeai.agent.graph as graph_module
from forgeai.agent.graph import build_agent_graph


class FakePatchPreparationService:
    """Marker dependency; the preparation node is replaced in these graph tests."""


def build_test_graph(monkeypatch, *, worker_calls: list[str]):
    """Build the real graph topology with deterministic node implementations."""

    monkeypatch.setattr(graph_module, "prepare_task_node", lambda state: {"status": "task_prepared", "error": ""})
    monkeypatch.setattr(graph_module, "create_sandbox_node", lambda **kwargs: lambda state: {"sandbox_id": "sandbox-e2e", "status": "sandbox_created"})
    monkeypatch.setattr(graph_module, "create_repository_clone_node", lambda **kwargs: lambda state: {"repository_commit_sha": "abc123", "status": "repository_cloned"})
    monkeypatch.setattr(graph_module, "create_repository_inspection_node", lambda **kwargs: lambda state: {"status": "repository_inspected"})
    monkeypatch.setattr(graph_module, "create_repository_context_node", lambda **kwargs: lambda state: {"repository_context_status": "available", "repository_context_files": [], "status": "context_built"})
    monkeypatch.setattr(graph_module, "create_planner_node", lambda agent: lambda state: {"plan": {"objective": "test"}})
    monkeypatch.setattr(graph_module, "create_researcher_node", lambda agent: lambda state: {"research": {"summary": "test"}})
    monkeypatch.setattr(graph_module, "create_coder_node", lambda agent: lambda state: {"code_changes": {"summary": "safe change", "changes": [], "tests_to_run": [], "risks": []}})
    monkeypatch.setattr(graph_module, "create_reviewer_node", lambda agent: lambda state: {"review": {"decision": "approved", "summary": "The proposed patch is approved.", "findings": [], "strengths": [], "tests_to_run": []}, "review_attempts": 1, "status": "review_completed"})
    monkeypatch.setattr(graph_module, "create_patch_preparation_node", lambda service: lambda state: {"patch": "diff --git a/file.py b/file.py\n", "patch_sha256": "a" * 64, "allowed_paths": ["file.py"], "status": "patch_prepared"})
    monkeypatch.setattr(graph_module, "create_approval_node", lambda session_factory: lambda state: {"approval_id": "approval-e2e", "status": "awaiting_approval"})

    def human_approval_node(state):
        decision = interrupt({"approval_id": state["approval_id"], "patch_sha256": state["patch_sha256"]})
        if decision == "approve":
            return {"human_approval_status": "approved", "status": "approval_granted"}
        return {"human_approval_status": "rejected", "status": "rejected"}

    monkeypatch.setattr(graph_module, "create_human_approval_node", lambda session_factory: human_approval_node)
    monkeypatch.setattr(graph_module, "create_execution_record_node", lambda session_factory: lambda state: {"execution_id": "execution-e2e", "execution_status": "pending", "status": "execution_pending"})

    def execute_approved_patch_node(state):
        worker_calls.append(state["execution_id"])
        return {"execution_status": "succeeded", "execution_result": {"success": True, "changed_files": ["file.py"]}, "status": "succeeded", "error": ""}

    monkeypatch.setattr(graph_module, "create_approved_patch_execution_node", lambda session_factory, worker_factory: execute_approved_patch_node)

    return build_agent_graph(
        planner_agent=MagicMock(),
        researcher_agent=MagicMock(),
        coder_agent=MagicMock(),
        reviewer_agent=MagicMock(),
        sandbox_provider=MagicMock(),
        checkpointer=MemorySaver(),
        session_factory=lambda: None,
        patch_preparation_service=FakePatchPreparationService(),
        execution_worker_factory=lambda execution_service: MagicMock(),
    )


@pytest.fixture
def initial_state():
    return {
        "task_id": "task-e2e",
        "task_description": "Verify approval-gated execution.",
        "agent_run_id": "run-e2e",
        "repository_url": "https://example.com/repo.git",
    }


@pytest.mark.unit
def test_approved_graph_resumes_and_executes_patch(monkeypatch, initial_state):
    worker_calls: list[str] = []
    graph = build_test_graph(monkeypatch, worker_calls=worker_calls)
    config = {"configurable": {"thread_id": "run-e2e-approved"}}

    paused = graph.invoke(initial_state, config=config)

    assert paused["approval_id"] == "approval-e2e"
    assert paused["patch_sha256"] == "a" * 64
    assert paused["status"] == "awaiting_approval"
    assert paused.get("__interrupt__")
    assert worker_calls == []

    completed = graph.invoke(Command(resume="approve"), config=config)

    assert completed["human_approval_status"] == "approved"
    assert completed["execution_id"] == "execution-e2e"
    assert completed["execution_status"] == "succeeded"
    assert completed["status"] == "succeeded"
    assert worker_calls == ["execution-e2e"]


@pytest.mark.unit
def test_rejected_graph_resumes_without_executing_patch(monkeypatch, initial_state):
    worker_calls: list[str] = []
    graph = build_test_graph(monkeypatch, worker_calls=worker_calls)
    config = {"configurable": {"thread_id": "run-e2e-rejected"}}

    paused = graph.invoke(initial_state, config=config)
    assert paused.get("__interrupt__")

    rejected = graph.invoke(Command(resume="reject"), config=config)

    assert rejected["human_approval_status"] == "rejected"
    assert rejected["status"] == "rejected"
    assert "execution_id" not in rejected
    assert worker_calls == []
