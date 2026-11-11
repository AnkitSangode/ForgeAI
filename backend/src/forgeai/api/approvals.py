
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from forgeai.api.dependencies.authorization import require_reviewer
from forgeai.api.schemas.approval import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalRead,
)
from forgeai.application.patch_approval_service import (
    ApprovalAlreadyDecidedError,
    PatchApprovalNotFoundError,
    PatchApprovalService,
    PatchApprovalStateError,
)
from forgeai.infrastructure.models.user import User
from forgeai.infrastructure.repositories.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)
from forgeai.infrastructure.repositories.patch_approval_repository import (
    SQLAlchemyPatchApprovalRepository,
)
from forgeai.infrastructure.session import get_db


router = APIRouter(
    prefix="/api/v1/approvals",
    tags=["approvals"],
)


def get_patch_approval_service(
    db: Annotated[Session, Depends(get_db)],
) -> PatchApprovalService:
    return PatchApprovalService(
        session=db,
        approval_repository=SQLAlchemyPatchApprovalRepository(db),
        agent_run_repository=SQLAlchemyAgentRunRepository(db),
    )


@router.get(
    "/{approval_id}",
    response_model=ApprovalRead,
)
def get_approval(
    approval_id: UUID,
    service: Annotated[
        PatchApprovalService,
        Depends(get_patch_approval_service),
    ],
    reviewer: Annotated[User, Depends(require_reviewer)],
) -> ApprovalRead:
    try:
        approval = service.get_approval(str(approval_id))

    except PatchApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found.",
        ) from None

    return ApprovalRead(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=approval.status.value,
        approved_by=approval.approved_by,
        decided_at=approval.decided_at,
        consumed_at=approval.consumed_at,
    )


@router.post(
    "/{approval_id}/decision",
    response_model=ApprovalRead,
)
def decide_approval(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    service: Annotated[
        PatchApprovalService,
        Depends(get_patch_approval_service),
    ],
    reviewer: Annotated[User, Depends(require_reviewer)],
) -> ApprovalRead:
    try:
        approval = service.decide_approval(
            approval_id=str(approval_id),
            approved=payload.decision == ApprovalDecision.APPROVE,
            actor_id=str(reviewer.id),
        )

    except PatchApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found.",
        ) from None

    except ApprovalAlreadyDecidedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This approval has already been decided.",
        ) from None

    except PatchApprovalStateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval cannot be decided in its current state.",
        ) from None

    return ApprovalRead(
        approval_id=approval.approval_id,
        task_id=approval.task_id,
        agent_run_id=approval.agent_run_id,
        patch_sha256=approval.patch_sha256,
        status=approval.status.value,
        approved_by=approval.approved_by,
        decided_at=approval.decided_at,
        consumed_at=approval.consumed_at,
    )
