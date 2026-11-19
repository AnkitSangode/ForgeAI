from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forgeai.api.approvals import (
    get_patch_approval_service,
    router,
)
from forgeai.api.dependencies.authorization import require_reviewer
from forgeai.application.agent_run_service import AgentRunStatus
from forgeai.application.patch_approval_service import (
    ApprovalAlreadyDecidedError,
    PatchApprovalNotFoundError,
)
from forgeai.domain.patch_approval import ApprovalStatus, PatchApproval
from forgeai.infrastructure.models.user import User, UserRole
from forgeai.infrastructure.session import get_db


@dataclass
class FakeRun:
    id: str
    task_id: str
    thread_id: str
    status: AgentRunStatus


class FakeGraph:
    def __init__(self, interrupted=True):
        self.interrupted = interrupted
        self.invocations = []

    def get_state(self, config):
        return SimpleNamespace(
            tasks=[
                SimpleNamespace(
                    interrupts=[
                        SimpleNamespace(value={"approval_id": self.approval_id})
                    ] if self.interrupted else []
                )
            ]
        )

    def invoke(self, command, config):
        self.invocations.append((command, config))
        self.interrupted = False
        return {"status": "approval_granted"}


class FakeAgentRunService:
    run = None
    transitions = []

    def __init__(self, session):
        pass

    def get_run(self, run_id):
        assert self.run is not None
        assert run_id == self.run.id
        return self.run

    def update_status(self, run_id, status):
        self.transitions.append((run_id, status))
        self.run.status = status
        return self.run


@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(router)
    application.state.graph = FakeGraph()
    application.dependency_overrides[get_db] = lambda: object()
    application.dependency_overrides[require_reviewer] = lambda: User(
        id=uuid4(),
        email="reviewer@example.com",
        password_hash="unused",
        is_active=True,
        role=UserRole.REVIEWER,
    )
    FakeAgentRunService.run = None
    FakeAgentRunService.transitions = []
    monkeypatch.setattr(
        "forgeai.api.approvals.AgentRunService",
        FakeAgentRunService,
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def approval():
    return PatchApproval(
        approval_id=str(uuid4()),
        task_id=str(uuid4()),
        agent_run_id=str(uuid4()),
        patch_sha256="a" * 64,
        status=ApprovalStatus.PENDING,
        approved_by=None,
        decided_at=None,
        consumed_at=None,
    )


class FakeApprovalService:
    def __init__(self, approval):
        self.approval = approval

    def decide_approval(self, approval_id, approved, actor_id):
        if self.approval.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyDecidedError("Already decided")
        self.approval = PatchApproval(
            **{
                **self.approval.__dict__,
                "status": ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
                "approved_by": actor_id,
                "decided_at": datetime.now(UTC),
            }
        )
        return self.approval

    def get_approval(self, approval_id):
        if approval_id != self.approval.approval_id:
            raise PatchApprovalNotFoundError("Not found")
        return self.approval


def install_approval_service(app, service):
    app.dependency_overrides[get_patch_approval_service] = lambda: service


def setup_run(approval, graph=None):
    if graph is not None:
        graph.approval_id = approval.approval_id
    FakeAgentRunService.run = FakeRun(
        id=approval.agent_run_id,
        task_id=approval.task_id,
        thread_id=str(uuid4()),
        status=AgentRunStatus.AWAITING_APPROVAL,
    )


def test_approved_decision_resumes_the_persisted_run(app, client, approval):
    service = FakeApprovalService(approval)
    install_approval_service(app, service)
    setup_run(approval, app.state.graph)

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert len(app.state.graph.invocations) == 1
    command, config = app.state.graph.invocations[0]
    assert config["configurable"]["thread_id"] == FakeAgentRunService.run.thread_id
    assert command.resume is True
    # Execution worker, not the approval endpoint, advances the run to EXECUTING.
    assert FakeAgentRunService.run.status == AgentRunStatus.AWAITING_APPROVAL


def test_rejected_decision_resumes_graph_and_marks_run_rejected(app, client, approval):
    service = FakeApprovalService(approval)
    install_approval_service(app, service)
    setup_run(approval, app.state.graph)

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert len(app.state.graph.invocations) == 1
    assert FakeAgentRunService.run.status == AgentRunStatus.REJECTED


def test_same_decision_retry_does_not_resume_twice(app, client, approval):
    service = FakeApprovalService(approval)
    install_approval_service(app, service)
    setup_run(approval, app.state.graph)

    first = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "approve"},
    )
    second = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "approve"},
    )

    assert first.status_code == second.status_code == 200
    assert len(app.state.graph.invocations) == 1


def test_conflicting_retry_returns_409(app, client, approval):
    approval = PatchApproval(
        **{**approval.__dict__, "status": ApprovalStatus.APPROVED}
    )
    service = FakeApprovalService(approval)
    install_approval_service(app, service)
    setup_run(approval, app.state.graph)

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "reject"},
    )

    assert response.status_code == 409
    assert app.state.graph.invocations == []


def test_missing_graph_returns_503_before_decision(app, client, approval):
    app.state.graph = None
    service = FakeApprovalService(approval)
    install_approval_service(app, service)

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 503
    assert approval.status == ApprovalStatus.PENDING


def test_invalid_decision_returns_422(app, client, approval):
    service = FakeApprovalService(approval)
    install_approval_service(app, service)

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        json={"decision": "maybe"},
    )

    assert response.status_code == 422
