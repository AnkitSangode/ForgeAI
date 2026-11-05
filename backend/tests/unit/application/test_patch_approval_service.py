from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from forgeai.application.patch_approval_service import (
    ApprovalAlreadyDecidedError,
    ApprovalConsumptionError,
    ApprovalNotFoundError,
    PatchApprovalService,
)
from forgeai.domain.patch_approval import (
    ApprovalStatus,
    PatchApproval,
)


def make_pending_approval() -> PatchApproval:
    return PatchApproval(
        approval_id=str(uuid4()),
        task_id=str(uuid4()),
        patch_sha256="a" * 64,
        status=ApprovalStatus.PENDING,
        approved_by=None,
        decided_at=None,
        consumed_at=None,
    )


def test_decide_approval_approves_pending_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_pending_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    result = service.decide_approval(
        approval_id=approval.approval_id,
        approved=True,
        actor_id="user-123",
    )

    assert result.status == ApprovalStatus.APPROVED
    assert result.approved_by == "user-123"
    assert result.decided_at is not None
    assert result.decided_at.tzinfo == UTC

    repository.get_by_id_for_update.assert_called_once_with(UUID(approval.approval_id))
    repository.update.assert_called_once_with(result)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_decide_approval_rejects_pending_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_pending_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    result = service.decide_approval(
        approval_id=approval.approval_id,
        approved=False,
        actor_id="user-123",
    )

    assert result.status == ApprovalStatus.REJECTED
    assert result.approved_by == "user-123"
    repository.update.assert_called_once_with(result)
    session.commit.assert_called_once()


def test_decide_approval_raises_when_approval_not_found() -> None:
    session = MagicMock()
    repository = MagicMock()
    repository.get_by_id_for_update.return_value = None

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalNotFoundError):
        service.decide_approval(
            approval_id=str(uuid4()),
            approved=True,
            actor_id="user-123",
        )

    repository.update.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once()


def test_decide_approval_rejects_already_decided_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_pending_approval()

    decided_approval = PatchApproval(
        **{
            **approval.__dict__,
            "status": ApprovalStatus.APPROVED,
            "approved_by": "another-user",
        }
    )

    repository.get_by_id_for_update.return_value = decided_approval

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalAlreadyDecidedError):
        service.decide_approval(
            approval_id=approval.approval_id,
            approved=False,
            actor_id="user-123",
        )

    repository.update.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once()


def test_decide_approval_requires_actor_id() -> None:
    session = MagicMock()
    repository = MagicMock()

    service = PatchApprovalService(session, repository)

    with pytest.raises(ValueError, match="actor ID"):
        service.decide_approval(
            approval_id=str(uuid4()),
            approved=True,
            actor_id=" ",
        )

    repository.get_by_id_for_update.assert_not_called()
    session.rollback.assert_called_once()


def test_create_approval_creates_pending_approval() -> None:
    session = MagicMock()
    repository = MagicMock()

    service = PatchApprovalService(
        session=session,
        repository=repository,
    )

    task_id = "12345678-1234-5678-1234-567812345678"
    patch_sha256 = "a" * 64

    result = service.create_approval(
        task_id=task_id,
        patch_sha256=patch_sha256,
    )

    assert result.task_id == task_id
    assert result.patch_sha256 == patch_sha256
    assert result.status == ApprovalStatus.PENDING
    assert result.approved_by is None
    assert result.decided_at is None
    assert result.consumed_at is None

    UUID(result.approval_id)

    repository.create.assert_called_once_with(result)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_create_approval_rolls_back_on_failure() -> None:
    session = MagicMock()
    repository = MagicMock()

    repository.create.side_effect = RuntimeError("Database failure")

    service = PatchApprovalService(
        session=session,
        repository=repository,
    )

    try:
        service.create_approval(
            task_id="12345678-1234-5678-1234-567812345678",
            patch_sha256="a" * 64,
        )
        raise AssertionError("Expected RuntimeError")
    except RuntimeError as exc:
        assert str(exc) == "Database failure"

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def make_approved_approval() -> PatchApproval:
    approval = make_pending_approval()

    return PatchApproval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        patch_sha256=approval.patch_sha256,
        status=ApprovalStatus.APPROVED,
        approved_by="user-123",
        decided_at=datetime.now(UTC),
    )


def test_consume_approval_successfully() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_approved_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    result = service.consume_approval(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        patch_sha256=approval.patch_sha256,
    )

    assert result.consumed_at is not None
    assert result.status == ApprovalStatus.APPROVED

    repository.get_by_id_for_update.assert_called_once_with(UUID(approval.approval_id))
    repository.update.assert_called_once_with(result)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_consume_approval_rejects_unknown_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    repository.get_by_id_for_update.return_value = None

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalConsumptionError):
        service.consume_approval(
            approval_id=str(uuid4()),
            task_id=str(uuid4()),
            patch_sha256="a" * 64,
        )

    repository.update.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_wrong_task() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_approved_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalConsumptionError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=str(uuid4()),
            patch_sha256=approval.patch_sha256,
        )

    repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_wrong_fingerprint() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_approved_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalConsumptionError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            patch_sha256="b" * 64,
        )

    repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_pending_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_pending_approval()

    repository.get_by_id_for_update.return_value = approval

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalConsumptionError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            patch_sha256=approval.patch_sha256,
        )

    repository.update.assert_not_called()
    session.rollback.assert_called_once()


def test_consume_approval_rejects_already_consumed_approval() -> None:
    session = MagicMock()
    repository = MagicMock()
    approval = make_approved_approval()

    consumed_approval = replace(
        approval,
        consumed_at=datetime.now(UTC),
    )

    repository.get_by_id_for_update.return_value = consumed_approval

    service = PatchApprovalService(session, repository)

    with pytest.raises(ApprovalConsumptionError):
        service.consume_approval(
            approval_id=approval.approval_id,
            task_id=approval.task_id,
            patch_sha256=approval.patch_sha256,
        )

    repository.update.assert_not_called()
    session.rollback.assert_called_once()
