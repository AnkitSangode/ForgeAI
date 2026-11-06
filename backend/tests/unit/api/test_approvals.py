from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forgeai.api.approvals import router
from forgeai.api.dependencies.auth import get_current_user
from forgeai.api.dependencies.authorization import require_reviewer
from forgeai.application.patch_approval_service import (
    ApprovalAlreadyDecidedError,
    ApprovalNotFoundError,
    PatchApprovalService,
)
from forgeai.domain.patch_approval import ApprovalStatus
from forgeai.infrastructure.models.user import User, UserRole
from forgeai.infrastructure.session import get_db


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    return application


@pytest.fixture
def client(app):
    app.dependency_overrides[get_db] = lambda: object()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def reviewer():
    return User(
        id=uuid4(),
        email="reviewer@example.com",
        password_hash="not-used",
        is_active=True,
        role=UserRole.REVIEWER,
    )


@pytest.fixture
def regular_user():
    return User(
        id=uuid4(),
        email="user@example.com",
        password_hash="not-used",
        is_active=True,
        role=UserRole.USER,
    )


@pytest.fixture
def pending_approval():
    return {
        "approval_id": str(uuid4()),
        "task_id": str(uuid4()),
        "patch_sha256": "a" * 64,
        "status": ApprovalStatus.PENDING,
        "approved_by": None,
        "decided_at": None,
        "consumed_at": None,
    }


def approval_entity(data):
    from forgeai.domain.patch_approval import PatchApproval

    return PatchApproval(**data)


def test_get_approval_success(app, client, reviewer, pending_approval, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: reviewer

    def fake_get_approval(self, approval_id):
        assert approval_id == pending_approval["approval_id"]
        return approval_entity(pending_approval)

    monkeypatch.setattr(PatchApprovalService, "get_approval", fake_get_approval)

    response = client.get(f"/api/v1/approvals/{pending_approval['approval_id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["patch_sha256"] == "a" * 64


def test_get_approval_not_found(app, client, reviewer, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: reviewer

    def fake_get_approval(self, approval_id):
        raise ApprovalNotFoundError("Approval not found")

    monkeypatch.setattr(PatchApprovalService, "get_approval", fake_get_approval)

    response = client.get(f"/api/v1/approvals/{uuid4()}")

    assert response.status_code == 404



def test_reviewer_can_approve(
    app,
    client,
    reviewer,
    pending_approval,
    monkeypatch,
):
    # 1. Bypass authentication and provide an authorized reviewer.
    app.dependency_overrides[require_reviewer] = lambda: reviewer

    # 2. Mock the application service's decision method.
    def fake_decide_approval(
        self,
        approval_id,
        approved,
        actor_id,
    ):
        assert approval_id == pending_approval["approval_id"]
        assert approved is True
        assert actor_id == str(reviewer.id)

        return approval_entity(
            {
                **pending_approval,
                "status": ApprovalStatus.APPROVED,
                "approved_by": actor_id,
                "decided_at": datetime.now(UTC),
            }
        )

    # 3. Replace the real service method with our mock.
    monkeypatch.setattr(
        PatchApprovalService,
        "decide_approval",
        fake_decide_approval,
    )

    # 4. Send the approval request.
    response = client.post(
        f"/api/v1/approvals/{pending_approval['approval_id']}/decision",
        json={"decision": "approve"},
    )

    # 5. Verify the API response.
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["approved_by"] == str(reviewer.id)



def test_reviewer_can_reject(app, client, reviewer, pending_approval, monkeypatch):
    app.dependency_overrides[require_reviewer] = lambda: reviewer

    def fake_decide_approval(self, approval_id, approved, actor_id):
        assert approved is False

        return approval_entity(
            {
                **pending_approval,
                "status": ApprovalStatus.REJECTED,
                "approved_by": actor_id,
                "decided_at": datetime.now(UTC),
            }
        )

    monkeypatch.setattr(
        PatchApprovalService,
        "decide_approval",
        fake_decide_approval,
    )

    response = client.post(
        f"/api/v1/approvals/{pending_approval['approval_id']}/decision",
        json={"decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_already_decided_approval_returns_409(
    app, client, reviewer, pending_approval, monkeypatch
):
    app.dependency_overrides[require_reviewer] = lambda: reviewer

    def fake_decide_approval(self, approval_id, approved, actor_id):
        raise ApprovalAlreadyDecidedError("Already decided")

    monkeypatch.setattr(
        PatchApprovalService,
        "decide_approval",
        fake_decide_approval,
    )

    response = client.post(
        f"/api/v1/approvals/{pending_approval['approval_id']}/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 409


def test_decision_approval_not_found(app, client, reviewer, monkeypatch):
    app.dependency_overrides[require_reviewer] = lambda: reviewer

    def fake_decide_approval(self, approval_id, approved, actor_id):
        raise ApprovalNotFoundError("Not found")

    monkeypatch.setattr(
        PatchApprovalService,
        "decide_approval",
        fake_decide_approval,
    )

    response = client.post(
        f"/api/v1/approvals/{uuid4()}/decision",
        json={"decision": "approve"},
    )

    assert response.status_code == 404


def test_invalid_decision_returns_422(app, client, reviewer, pending_approval):
    app.dependency_overrides[require_reviewer] = lambda: reviewer

    response = client.post(
        f"/api/v1/approvals/{pending_approval['approval_id']}/decision",
        json={"decision": "maybe"},
    )

    assert response.status_code == 422


def test_invalid_approval_uuid_returns_422(client, app, reviewer):
    app.dependency_overrides[get_current_user] = lambda: reviewer

    response = client.get("/api/v1/approvals/not-a-uuid")

    assert response.status_code == 422
