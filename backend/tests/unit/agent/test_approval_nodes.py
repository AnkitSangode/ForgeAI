
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from forgeai.agent.approval_nodes import (
    create_approval_node,
    create_human_approval_node,
)
from forgeai.domain.patch_approval import ApprovalStatus, PatchApproval
from forgeai.application.patch_approval_service import (
    PatchApprovalStateError,
)


@pytest.fixture
def identifiers():
    return {
        "task_id": str(uuid4()),
        "agent_run_id": str(uuid4()),
        "patch_sha256": "a" * 64,
        "approval_id": str(uuid4()),
    }


@pytest.fixture
def state(identifiers):
    return {
        **identifiers,
        "status": "awaiting_approval",
    }


@pytest.fixture
def session_factory():
    session = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = session
    return factory


def make_approval(identifiers, status):
    return PatchApproval(
        approval_id=identifiers["approval_id"],
        task_id=identifiers["task_id"],
        agent_run_id=identifiers["agent_run_id"],
        patch_sha256=identifiers["patch_sha256"],
        status=status,
        approved_by="reviewer-123",
        decided_at=None,
        consumed_at=None,
    )


@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_create_approval_success(
    service_class,
    session_factory,
    identifiers,
    state,
):
    service = service_class.return_value
    service.create_approval.return_value = make_approval(
        identifiers,
        ApprovalStatus.PENDING,
    )

    node = create_approval_node(session_factory)
    result = node(state)

    assert result["approval_id"] == identifiers["approval_id"]
    assert result["status"] == "awaiting_approval"

    service.create_approval.assert_called_once_with(
        task_id=identifiers["task_id"],
        agent_run_id=identifiers["agent_run_id"],
        patch_sha256=identifiers["patch_sha256"],
    )


def test_create_approval_rejects_missing_state(
    session_factory,
):
    node = create_approval_node(session_factory)

    result = node({"task_id": str(uuid4())})

    assert result["status"] == "failed"
    session_factory.assert_not_called()


@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_create_approval_handles_service_failure(
    service_class,
    session_factory,
    state,
):
    service_class.return_value.create_approval.side_effect = ValueError(
        "Database error"
    )

    node = create_approval_node(session_factory)
    result = node(state)

    assert result["status"] == "failed"
    assert "Database error" in result["error"]


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_accepts_persisted_approval(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    interrupt_mock.return_value = {"approved": True}

    service = service_class.return_value
    service.get_approval.return_value = make_approval(
        identifiers,
        ApprovalStatus.APPROVED,
    )

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["human_approval_status"] == "approved"
    assert result["status"] == "approval_granted"

    interrupt_mock.assert_called_once()
    service.get_approval.assert_called_once_with(
        identifiers["approval_id"]
    )


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_rejects_persisted_rejection(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    service = service_class.return_value
    service.get_approval.return_value = make_approval(
        identifiers,
        ApprovalStatus.REJECTED,
    )

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["human_approval_status"] == "rejected"
    assert result["status"] == "rejected"


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_rejects_pending_status(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    service = service_class.return_value
    service.get_approval.return_value = make_approval(
        identifiers,
        ApprovalStatus.PENDING,
    )

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["status"] == "failed"
    assert "not been approved" in result["error"]


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_rejects_wrong_patch_fingerprint(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    approval = make_approval(
        identifiers,
        ApprovalStatus.APPROVED,
    )

    approval = PatchApproval(
        **{
            **approval.__dict__,
            "patch_sha256": "b" * 64,
        }
    )

    service_class.return_value.get_approval.return_value = approval

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["status"] == "failed"
    assert "fingerprint" in result["error"]


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_rejects_wrong_task(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    approval = make_approval(
        identifiers,
        ApprovalStatus.APPROVED,
    )

    approval = PatchApproval(
        **{
            **approval.__dict__,
            "task_id": str(uuid4()),
        }
    )

    service_class.return_value.get_approval.return_value = approval

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["status"] == "failed"
    assert "different task" in result["error"]


@patch("forgeai.agent.approval_nodes.interrupt")
@patch("forgeai.agent.approval_nodes.PatchApprovalService")
def test_human_approval_rejects_wrong_agent_run(
    service_class,
    interrupt_mock,
    session_factory,
    identifiers,
    state,
):
    approval = make_approval(
        identifiers,
        ApprovalStatus.APPROVED,
    )

    approval = PatchApproval(
        **{
            **approval.__dict__,
            "agent_run_id": str(uuid4()),
        }
    )

    service_class.return_value.get_approval.return_value = approval

    node = create_human_approval_node(session_factory)
    result = node(state)

    assert result["status"] == "failed"
    assert "different agent run" in result["error"]


def test_human_approval_rejects_missing_state(
    session_factory,
):
    node = create_human_approval_node(session_factory)

    result = node({})

    assert result["status"] == "failed"
    session_factory.assert_not_called()
