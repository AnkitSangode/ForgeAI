
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from forgeai.api.schemas.agent_run import AgentRunRead
from forgeai.api.dependencies.auth import get_current_user
from forgeai.infrastructure.models.user import User
from forgeai.application.agent_run_service import (
    AgentRunNotFoundError,
    AgentRunService,
    AgentRunStatus,
)
from forgeai.application.task_service import TaskNotFoundError, TaskService
from forgeai.infrastructure.session import SessionLocal, get_db


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["agent-runs"],
)

runs_collection_router = APIRouter(
    prefix="/api/v1/runs",
    tags=["agent-runs"],
)


@runs_collection_router.get("", response_model=list[AgentRunRead])
def list_agent_runs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    task_id: UUID | None = None,
) -> list[AgentRunRead]:
    runs = AgentRunService(db).list_runs(
        offset=offset,
        limit=limit,
        task_id=task_id,
    )
    return [AgentRunRead.model_validate(run) for run in runs]


@runs_collection_router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(
    run_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentRunRead:
    try:
        run = AgentRunService(db).get_run(str(run_id))
    except AgentRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return AgentRunRead.model_validate(run)


def determine_run_status(result: dict) -> AgentRunStatus:
    """Determine the AgentRun status from the graph's final state."""

    result_status = result.get("status")
    review = result.get("review") or {}
    review_decision = review.get("decision")

    if result_status in {"failed", "review_attempts_exhausted"}:
        return AgentRunStatus.FAILED

    if result_status == "rejected" or review_decision == "rejected":
        return AgentRunStatus.REJECTED

    if review_decision == "approved":
        return AgentRunStatus.AWAITING_APPROVAL

    if result_status == "succeeded":
        return AgentRunStatus.SUCCEEDED

    return AgentRunStatus.FAILED


def is_graph_interrupted(graph, config: dict) -> bool:
    """Check whether LangGraph is currently paused by an interrupt."""

    snapshot = graph.get_state(config)

    return any(
        task.interrupts
        for task in snapshot.tasks
    )


def execute_agent_run(
    graph,
    telemetry,
    task_id: str,
    run_id: str,
    thread_id: str,
    task_description: str,
    repository_url: str,
) -> None:
    """Execute a run after returning the HTTP response to the client."""
    with SessionLocal() as session:
        service = AgentRunService(session)
        service.update_status(run_id, AgentRunStatus.RUNNING)
        initial_state = {
            "task_id": task_id,
            "agent_run_id": run_id,
            "task_description": task_description,
            "repository_url": repository_url,
        }
        config = {"configurable": {"thread_id": thread_id}}
        try:
            if telemetry is not None:
                with telemetry.span(
                    name="forgeai.agent_run",
                    input_data={"operation": "graph.invoke"},
                    metadata={
                        "task_id": task_id,
                        "agent_run_id": run_id,
                        "thread_id": thread_id,
                    },
                ) as observation:
                    result = graph.invoke(initial_state, config=config)
                    final_status = (
                        AgentRunStatus.AWAITING_APPROVAL
                        if is_graph_interrupted(graph, config)
                        else determine_run_status(result)
                    )
                    observation.update(output={"status": final_status.value})
            else:
                result = graph.invoke(initial_state, config=config)
                final_status = (
                    AgentRunStatus.AWAITING_APPROVAL
                    if is_graph_interrupted(graph, config)
                    else determine_run_status(result)
                )
            service.update_status(run_id, final_status)
        except Exception:
            logger.exception(
                "Agent execution failed. run_id=%s task_id=%s",
                run_id,
                task_id,
            )
            try:
                service.update_status(run_id, AgentRunStatus.FAILED)
            except Exception:
                logger.exception("Failed to persist failed run status. run_id=%s", run_id)


@router.post(
    "/{task_id}/runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
)
def start_agent_run(
    task_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentRunRead:
    """Create an AgentRun and execute the LangGraph workflow."""

    # 1. Retrieve the requested task.
    task_service = TaskService(db)

    try:
        task = task_service.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # 2. Verify that the graph is available.
    graph = getattr(request.app.state, "graph", None)

    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent graph is not available.",
        )

    telemetry = getattr(request.app.state, "telemetry", None)

    with SessionLocal() as session:
        run_service = AgentRunService(session)
        run = run_service.create_run(str(task.id))
        background_tasks.add_task(
            execute_agent_run,
            graph,
            telemetry,
            str(task.id),
            str(run.id),
            run.thread_id,
            task.description,
            str(task.repository_url),
        )
        return AgentRunRead.model_validate(run)
