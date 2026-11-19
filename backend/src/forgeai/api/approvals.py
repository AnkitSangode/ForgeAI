from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from langgraph.types import Command
from sqlalchemy.orm import Session

from forgeai.api.dependencies.authorization import require_reviewer
from forgeai.api.schemas.approval import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalRead,
)
from forgeai.application.agent_run_service import (
    AgentRunNotFoundError,
    AgentRunService,
    AgentRunStatus,
    InvalidAgentRunTransitionError,
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


def _is_graph_interrupted(graph: Any, config: dict) -> bool:
    """Return True only when this checkpoint has a pending LangGraph interrupt."""
    snapshot = graph.get_state(config)
    return any(task.interrupts for task in snapshot.tasks)


def _approval_read(approval) -> ApprovalRead:
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

    return _approval_read(approval)


@router.post(
    "/{approval_id}/decision",
    response_model=ApprovalRead,
)
def decide_approval(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
    service: Annotated[
        PatchApprovalService,
        Depends(get_patch_approval_service),
    ],
    db: Annotated[Session, Depends(get_db)],
    reviewer: Annotated[User, Depends(require_reviewer)],
) -> ApprovalRead:
    """Persist a reviewer decision and resume its associated graph thread.

    The run/thread association is loaded from the database. A client cannot
    choose which graph thread is resumed. Repeating the same decision is safe:
    if the decision was already persisted, the route resumes only if the graph
    still has the matching pending interrupt.
    """
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent graph is not available.",
        )

    approved = payload.decision == ApprovalDecision.APPROVE

    try:
        try:
            approval = service.decide_approval(
                approval_id=str(approval_id),
                approved=approved,
                actor_id=str(reviewer.id),
            )
        except ApprovalAlreadyDecidedError:
            # A retry after a lost HTTP response must not create a second
            # decision. Continue only when the persisted decision matches.
            approval = service.get_approval(str(approval_id))
            expected_status = "approved" if approved else "rejected"
            if approval.status.value != expected_status:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This approval has already been decided differently.",
                ) from None

        # Resolve the run from the approval's persisted foreign key.
        run_service = AgentRunService(db)
        run = run_service.get_run(approval.agent_run_id)

        if run.task_id != approval.task_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval and agent run do not belong to the same task.",
            )

        config = {"configurable": {"thread_id": run.thread_id}}

        # The execution worker will move an approved run from
        # AWAITING_APPROVAL -> EXECUTING when it claims the execution.
        # Do not resume twice if a prior request already passed the interrupt.
        if run.status == AgentRunStatus.AWAITING_APPROVAL:
            if _is_graph_interrupted(graph, config):
                resumed_state = graph.invoke(Command(resume=True), config=config)

                # A rejection ends the graph with status='rejected'. Persist
                # the matching AgentRun terminal status here.
                current_run = run_service.get_run(run.id)
                if not approved and current_run.status == AgentRunStatus.AWAITING_APPROVAL:
                    run_service.update_status(
                        run.id,
                        AgentRunStatus.REJECTED,
                    )
                elif (
                    approved
                    and isinstance(resumed_state, dict)
                    and resumed_state.get("status") == "failed"
                    and current_run.status == AgentRunStatus.AWAITING_APPROVAL
                ):
                    # Failures before the execution claim (e.g. an invalid
                    # fingerprint or inability to create an execution record)
                    # have no worker lifecycle to update the AgentRun. Once a
                    # worker has claimed it, that worker exclusively owns the
                    # EXECUTING -> SUCCEEDED/FAILED transition.
                    run_service.update_status(
                        run.id,
                        AgentRunStatus.FAILED,
                    )
            # If there is no interrupt, a previous request may already have
            # resumed this checkpoint. Leave the durable run state unchanged.
        elif run.status in {
            AgentRunStatus.EXECUTING,
            AgentRunStatus.SUCCEEDED,
            AgentRunStatus.REJECTED,
            AgentRunStatus.FAILED,
        }:
            # Terminal/in-progress retries are idempotent; never restart them.
            if run.status == AgentRunStatus.REJECTED and approved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="The agent run has already been rejected.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The agent run is not waiting for a human approval "
                    f"(current status: {run.status.value})."
                ),
            )

    except PatchApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found.",
        ) from None
    except (PatchApprovalStateError, AgentRunNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval or associated agent run is in an invalid state.",
        ) from None
    except InvalidAgentRunTransitionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent run cannot transition to the requested state.",
        ) from None
    except HTTPException:
        raise
    except Exception as exc:
        # The reviewer decision is already durable. A retry with the same
        # decision can safely re-enter this route and resume if still paused.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The decision was saved, but the agent workflow could not "
                "be resumed. Retry the same decision."
            ),
        ) from exc

    # Re-read so the response reflects any persisted state changes.
    approval = service.get_approval(str(approval_id))
    return _approval_read(approval)
