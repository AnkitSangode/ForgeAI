from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from forgeai.application.patch_approval_service import (
    ApprovalRunValidationError,
    PatchApprovalNotFoundError,
    PatchApprovalService,
    PatchApprovalStateError,
)
from forgeai.domain.agent_run import AgentRun, AgentRunStatus
from forgeai.domain.patch_approval import ApprovalStatus, PatchApproval
from forgeai.domain.patch_approval import ApprovalStatus


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def approval_repository():
    return MagicMock()


@pytest.fixture
def agent_run_repository():
    return MagicMock()


@pytest.fixture
def service(session, approval_repository, agent_run_repository):
    return PatchApprovalService(
        session=session,
        approval_repository=approval_repository,
        agent_run_repository=agent_run_repository,
    )


@pytest.fixture
def task_id():
    return str(uuid4())


@pytest.fixture
def agent_run(task_id):
    now = datetime.now(UTC)

    return AgentRun(
        id=str(uuid4()),
        task_id=task_id,
        thread_id=str(uuid4()),
        status=AgentRunStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def approval(task_id, agent_run):
    return PatchApproval(
        approval_id=str(uuid4()),
        task_id=task_id,
        agent_run_id=agent_run.id,
        patch_sha256="test-patch-hash",
        status=ApprovalStatus.PENDING,
        approved_by=None,
        decided_at=None,
        consumed_at=None,
    )


# ---------------------------------------------------------------------
# CREATE APPROVAL
# ---------------------------------------------------------------------


def test_create_approval_success(
    service,
    session,
    approval_repository,
    agent_run_repository,
    task_id,
    agent_run,
):
    agent_run_repository.get_by_id.return_value = agent_run

    # Mock repository persistence by returning the domain object.
    approval_repository.create.side_effect = lambda value: value

    result = service.create_approval(
        task_id=task_id,
        agent_run_id=agent_run.id,
        patch_sha256="test-patch-hash",
    )

    assert isinstance(result, PatchApproval)
    assert result.task_id == task_id
    assert result.agent_run_id == agent_run.id
    assert result.patch_sha256 == "test-patch-hash"
    assert result.status == ApprovalStatus.PENDING
    assert result.approved_by is None
    assert result.decided_at is None
    assert result.consumed_at is None

    agent_run_repository.get_by_id.assert_called_once()
    approval_repository.create.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_create_approval_rejects_empty_run_id(
    service,
    session,
    task_id,
):
    with pytest.raises(ApprovalRunValidationError):
        service.create_approval(
            task_id=task_id,
            agent_run_id="",
            patch_sha256="test-patch-hash",
        )

    session.rollback.assert_called_once()


def test_create_approval_rejects_invalid_run_uuid(
    service,
    session,
    task_id,
):
    with pytest.raises(ApprovalRunValidationError):
        service.create_approval(
            task_id=task_id,
            agent_run_id="invalid-uuid",
            patch_sha256="test-patch-hash",
        )

    session.rollback.assert_called_once()


def test_create_approval_rejects_missing_agent_run(
    service,
    session,
    agent_run_repository,
    task_id,
):
    agent_run_repository.get_by_id.return_value = None

    with pytest.raises(ApprovalRunValidationError):
        service.create_approval(
            task_id=task_id,
            agent_run_id=str(uuid4()),
            patch_sha256="test-patch-hash",
        )

    session.rollback.assert_called_once()


def test_create_approval_rejects_run_from_another_task(
    service,
    session,
    agent_run_repository,
    task_id,
    agent_run,
):
    agent_run_repository.get_by_id.return_value = agent_run

    with pytest.raises(ApprovalRunValidationError):
        service.create_approval(
            task_id=str(uuid4()),
            agent_run_id=agent_run.id,
            patch_sha256="test-patch-hash",
        )

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_create_approval_rejects_empty_patch_fingerprint(
    service,
    session,
    task_id,
    agent_run,
    agent_run_repository,
):
    agent_run_repository.get_by_id.return_value = agent_run

    with pytest.raises(ValueError):
        service.create_approval(
            task_id=task_id,
            agent_run_id=agent_run.id,
            patch_sha256="",
        )

    session.rollback.assert_called_once()


def test_create_approval_rolls_back_on_repository_failure(
    service,
    session,
    approval_repository,
    agent_run_repository,
    task_id,
    agent_run,
):
    agent_run_repository.get_by_id.return_value = agent_run
    approval_repository.create.side_effect = RuntimeError("Database failure")

    with pytest.raises(RuntimeError):
        service.create_approval(
            task_id=task_id,
            agent_run_id=agent_run.id,
            patch_sha256="test-patch-hash",
        )

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


# ---------------------------------------------------------------------
# DECIDE APPROVAL
# ---------------------------------------------------------------------


def test_decide_approval_success(
    service,
    session,
    approval_repository,
    approval,
):
    approval_repository.get_by_id_for_update.return_value = approval
    approval_repository.update.side_effect = lambda value: value

    result = service.decide_approval(
        approval_id=approval.approval_id,
        approved=True,
        actor_id="reviewer-123",
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.approved_by == "reviewer-123"
    assert result.decided_at is not None

    approval_repository.update.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_decide_approval_rejection(
    service,
    session,
    approval_repository,
    approval,
):
    approval_repository.get_by_id_for_update.return_value = approval
    approval_repository.update.side_effect = lambda value: value

    result = service.decide_approval(
        approval_id=approval.approval_id,
        approved=False,
        actor_id="reviewer-123",
    )

    assert result.status == ApprovalStatus.REJECTED
    assert result.approved_by == "reviewer-123"
    assert result.decided_at is not None

    session.commit.assert_called_once()


def test_decide_approval_already_decided(
    service,
    session,
    approval_repository,
    approval,
):
    decided_approval = PatchApproval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=ApprovalStatus.APPROVED,
        approved_by="reviewer-123",
        decided_at=datetime.now(UTC),
        consumed_at=None,
    )

    approval_repository.get_by_id.return_value = decided_approval

    with pytest.raises(PatchApprovalStateError):
        service.decide_approval(
            approval_id=approval.approval_id,
            approved=False,
            actor_id="reviewer-456",
        )

    approval_repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_decide_approval_rejects_empty_actor(
    service,
    session,
    approval_repository,
    approval,
):
    approval_repository.get_by_id_for_update.return_value = approval

    with pytest.raises(ValueError):
        service.decide_approval(
            approval_id=approval.approval_id,
            approved=True,
            actor_id="",
        )

    approval_repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_decide_approval_rolls_back_on_commit_failure(
    service,
    session,
    approval_repository,
    approval,
):
    approval_repository.get_by_id_for_update.return_value = approval
    approval_repository.update.side_effect = lambda value: value
    session.commit.side_effect = RuntimeError("Commit failed")

    with pytest.raises(RuntimeError):
        service.decide_approval(
            approval_id=approval.approval_id,
            approved=True,
            actor_id="reviewer-123",
        )

    session.rollback.assert_called_once()


# ---------------------------------------------------------------------
# CONSUME APPROVAL
# ---------------------------------------------------------------------


def test_consume_approval_success(
    service,
    session,
    approval_repository,
    approval,
):
    approved_approval = PatchApproval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=ApprovalStatus.APPROVED,
        approved_by="reviewer-123",
        decided_at=datetime.now(UTC),
        consumed_at=None,
    )

    approval_repository.get_by_id_for_update.return_value = approved_approval
    approval_repository.update.side_effect = lambda value: value

    result = service.consume_approval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.consumed_at is not None

    approval_repository.update.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    ("field", "incorrect_value"),
    [
        ("task_id", str(uuid4())),
        ("agent_run_id", str(uuid4())),
        ("patch_sha256", "different-patch-hash"),
    ],
)
def test_consume_approval_rejects_mismatched_identity(
    service,
    session,
    approval_repository,
    approval,
    field,
    incorrect_value,
):
    approved_approval = PatchApproval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=ApprovalStatus.APPROVED,
        approved_by="reviewer-123",
        decided_at=datetime.now(UTC),
        consumed_at=None,
    )

    approval_repository.get_by_id_for_update.return_value = approved_approval

    arguments = {
        "approval_id": approval.approval_id,
        "task_id": approval.task_id,
        "agent_run_id": approval.agent_run_id,
        "patch_sha256": approval.patch_sha256,
    }

    arguments[field] = incorrect_value

    with pytest.raises(PatchApprovalStateError):
        service.consume_approval(**arguments)

    approval_repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_pending_approval(
    service,
    session,
    approval_repository,
    approval,
):
    approval_repository.get_by_id_for_update.return_value = approval

    with pytest.raises(PatchApprovalStateError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            agent_run_id=approval.agent_run_id,
            patch_sha256=approval.patch_sha256,
        )

    approval_repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_already_consumed_approval(
    service,
    session,
    approval_repository,
    approval,
):
    consumed_approval = PatchApproval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=ApprovalStatus.APPROVED,
        approved_by="reviewer-123",
        decided_at=datetime.now(UTC),
        consumed_at=datetime.now(UTC),
    )

    approval_repository.get_by_id_for_update.return_value = consumed_approval

    with pytest.raises(PatchApprovalStateError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            agent_run_id=approval.agent_run_id,
            patch_sha256=approval.patch_sha256,
        )

    approval_repository.update.assert_not_called()
    session.rollback.assert_called_once()


# ---------------------------------------------------------------------
# GET APPROVAL
# ---------------------------------------------------------------------


def test_get_approval_success(
    service,
    approval_repository,
    approval,
):
    approval_repository.get_by_id.return_value = approval

    result = service.get_approval(approval.approval_id)

    assert result == approval
    approval_repository.get_by_id.assert_called_once()


def test_get_approval_not_found(
    service,
    approval_repository,
):
    approval_repository.get_by_id.return_value = None

    with pytest.raises(PatchApprovalNotFoundError):
        service.get_approval(str(uuid4()))


def test_get_approval_rejects_invalid_uuid(
    service,
    approval_repository,
):
    with pytest.raises(PatchApprovalNotFoundError):
        service.get_approval("not-a-valid-uuid")

    approval_repository.get_by_id.assert_not_called()


def test_create_approval_returns_existing_approval(
    service,
    approval_repository,
    agent_run_repository,
    valid_agent_run,
):
    task_id = valid_agent_run.task_id
    run_id = valid_agent_run.id
    patch_sha256 = "a" * 64

    existing_approval = PatchApproval(
        approval_id=str(uuid4()),
        task_id=task_id,
        agent_run_id=run_id,
        patch_sha256=patch_sha256,
        status=ApprovalStatus.PENDING,
        approved_by=None,
        decided_at=None,
        consumed_at=None,
    )

    agent_run_repository.get_by_id.return_value = valid_agent_run

    approval_repository.get_by_run_and_patch.return_value = (
        existing_approval
    )

    result = service.create_approval(
        task_id=task_id,
        agent_run_id=run_id,
        patch_sha256=patch_sha256,
    )

    assert result == existing_approval

    approval_repository.create.assert_not_called()


def test_create_approval_creates_new_record_when_not_existing(
    service,
    approval_repository,
    agent_run_repository,
    valid_agent_run,
):
    task_id = valid_agent_run.task_id
    run_id = valid_agent_run.id
    patch_sha256 = "b" * 64

    agent_run_repository.get_by_id.return_value = valid_agent_run
    approval_repository.get_by_run_and_patch.return_value = None

    approval_repository.create.side_effect = lambda approval: approval

    result = service.create_approval(
        task_id=task_id,
        agent_run_id=run_id,
        patch_sha256=patch_sha256,
    )

    assert result.status == ApprovalStatus.PENDING
    assert result.task_id == task_id
    assert result.agent_run_id == run_id
    assert result.patch_sha256 == patch_sha256

    approval_repository.create.assert_called_once()


def test_different_patch_creates_separate_approval(
    service,
    approval_repository,
    agent_run_repository,
    valid_agent_run,
):
    task_id = valid_agent_run.task_id
    run_id = valid_agent_run.id

    agent_run_repository.get_by_id.return_value = valid_agent_run
    approval_repository.get_by_run_and_patch.return_value = None
    approval_repository.create.side_effect = lambda approval: approval

    first = service.create_approval(
        task_id=task_id,
        agent_run_id=run_id,
        patch_sha256="a" * 64,
    )

    second = service.create_approval(
        task_id=task_id,
        agent_run_id=run_id,
        patch_sha256="b" * 64,
    )

    assert first.patch_sha256 != second.patch_sha256
    assert approval_repository.create.call_count == 2

