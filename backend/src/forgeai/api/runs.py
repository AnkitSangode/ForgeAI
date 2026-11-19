
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from forgeai.api.schemas.agent_run import AgentRunRead
from forgeai.application.agent_run_service import (
    AgentRunService,
    AgentRunStatus,
)
from forgeai.application.task_service import TaskNotFoundError, TaskService
from forgeai.infrastructure.session import SessionLocal, get_db


router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["agent-runs"],
)


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


@router.post(
    "/{task_id}/runs",
    response_model=AgentRunRead,
    status_code=status.HTTP_201_CREATED,
)
def start_agent_run(
    task_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
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

    # 3. Retrieve the shared telemetry instance.
    telemetry = getattr(request.app.state, "telemetry", None)

    # 4. Keep one database session and service instance for this request.
    with SessionLocal() as session:
        run_service = AgentRunService(session)

        run = run_service.create_run(str(task.id))

        run_service.update_status(
            run.id,
            AgentRunStatus.RUNNING,
        )

        # 5. Prepare the initial graph state.
        initial_state = {
            "task_id": str(task.id),
            "agent_run_id": str(run.id),
            "task_description": task.description,
            "repository_url": task.repository_url,
        }

        # 6. Use the persisted thread ID for checkpointing.
        config = {
            "configurable": {
                "thread_id": run.thread_id,
            }
        }

        try:
            if telemetry is not None:
                # Create a parent observation for the agent run.
                with telemetry.span(
                    name="forgeai.agent_run",
                    input_data={
                        "operation": "graph.invoke",
                    },
                    metadata={
                        "task_id": str(task.id),
                        "agent_run_id": str(run.id),
                        "thread_id": run.thread_id,
                    },
                ) as observation:

                    result = graph.invoke(
                        initial_state,
                        config=config,
                    )

                    # 7. Determine the final workflow status.
                    if is_graph_interrupted(graph, config):
                        final_status = AgentRunStatus.AWAITING_APPROVAL
                    else:
                        final_status = determine_run_status(result)

                    # Record safe execution metadata.
                    observation.update(
                        output={
                            "status": final_status.value,
                        },
                        metadata={
                            "interrupted": (
                                final_status
                                == AgentRunStatus.AWAITING_APPROVAL
                            ),
                        },
                    )

            else:
                result = graph.invoke(
                    initial_state,
                    config=config,
                )

                if is_graph_interrupted(graph, config):
                    final_status = AgentRunStatus.AWAITING_APPROVAL
                else:
                    final_status = determine_run_status(result)

            # 8. Persist the final status using the same service.
            updated_run = run_service.update_status(
                run.id,
                final_status,
            )

            return AgentRunRead.model_validate(updated_run)

        except Exception as exc:
            # 9. Mark the run as failed if execution raises an exception.
            try:
                run_service.update_status(
                    run.id,
                    AgentRunStatus.FAILED,
                )
            except Exception:
                # Preserve the original execution exception.
                pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution failed. Run ID: {run.id}",
            ) from exc
