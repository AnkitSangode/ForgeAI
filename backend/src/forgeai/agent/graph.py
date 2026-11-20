from collections.abc import Callable
from typing import Any, Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from forgeai.agent.approval_nodes import (
    create_approval_node,
    create_human_approval_node,
)
from forgeai.agent.coder import CoderAgent
from forgeai.agent.execution_nodes import (
    create_approved_patch_execution_node,
    create_execution_record_node,
)
from forgeai.agent.nodes import (
    create_coder_node,
    create_patch_preparation_node,
    create_planner_node,
    create_repository_clone_node,
    create_repository_context_node,
    create_repository_inspection_node,
    create_researcher_node,
    create_reviewer_node,
    prepare_task_node,
)
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.reviewer import ReviewerAgent
from forgeai.agent.reviewer_schema import ReviewResponse
from forgeai.agent.sandbox_nodes import create_sandbox_node
from forgeai.agent.state import ForgeAgentState
from forgeai.application.mcp.mcp_research_service import (
    MCPResearchService,
)
from forgeai.application.patch_preparation_service import PatchPreparationService
from forgeai.execution.sandbox.base import SandboxProvider
from forgeai.telemetry.opentelemetry import trace_graph_node


def route_after_prepare(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_sandbox_creation(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    if not state.get("sandbox_id"):
        return "stop"

    return "continue"


def route_after_clone(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    if not state.get("repository_commit_sha"):
        return "stop"

    return "continue"


def route_after_inspection(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_context_build(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_planning(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_research(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_coding(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
        return "stop"

    return "continue"


def route_after_review(
    state: ForgeAgentState,
    max_coding_attempts: int = 3,
) -> Literal[
    "approved",
    "changes_requested",
    "rejected",
    "retry_limit_reached",
    "stop",
]:
    """Route the workflow according to the review decision."""

    if state.get("status") == "failed":
        return "stop"

    review_data = state.get("review")

    if not review_data:
        return "stop"

    review = ReviewResponse.model_validate(review_data)

    if review.decision == "approved":
        return "approved"

    if review.decision == "rejected":
        return "rejected"

    if state.get("review_attempts", 0) >= max_coding_attempts:
        return "retry_limit_reached"

    return "changes_requested"



def route_after_patch_preparation(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed" or not state.get("patch_sha256"):
        return "stop"
    return "continue"


def route_after_human_approval(
    state: ForgeAgentState,
) -> Literal["approved", "rejected", "stop"]:
    if state.get("status") == "failed":
        return "stop"
    if state.get("human_approval_status") == "approved":
        return "approved"
    if state.get("human_approval_status") == "rejected":
        return "rejected"
    return "stop"


def route_after_execution_creation(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed" or not state.get("execution_id"):
        return "stop"
    return "continue"


def build_agent_graph(
    planner_agent: PlannerAgent,
    researcher_agent: ResearcherAgent,
    coder_agent: CoderAgent,
    reviewer_agent: ReviewerAgent,
    sandbox_provider: SandboxProvider,
    sandbox_timeout_seconds: int = 600,
    max_coding_attempts: int = 3,
    checkpointer: BaseCheckpointSaver | None = None,
    session_factory: Callable[[], Any] | None = None,
    patch_preparation_service: PatchPreparationService | None = None,
    execution_worker_factory: Callable[[Any], Any] | None = None,
    mcp_research_service: MCPResearchService | None = None,
    mcp_max_tool_calls: int = 10,
):
    """Build and compile the ForgeAI agent workflow."""

    if max_coding_attempts < 1:
        raise ValueError("max_coding_attempts must be at least 1.")

    approval_dependencies = (
        session_factory,
        patch_preparation_service,
        execution_worker_factory,
    )
    approval_pipeline_enabled = all(
        dependency is not None for dependency in approval_dependencies
    )
    if any(dependency is not None for dependency in approval_dependencies) and not approval_pipeline_enabled:
        raise ValueError(
            "session_factory, patch_preparation_service, and "
            "execution_worker_factory must be supplied together."
        )

    builder = StateGraph(ForgeAgentState)

    # Infrastructure nodes.
    sandbox_node = create_sandbox_node(
        sandbox_provider=sandbox_provider,
        timeout_seconds=sandbox_timeout_seconds,
    )

    clone_node = create_repository_clone_node(
        sandbox_provider=sandbox_provider,
    )

    inspection_node = create_repository_inspection_node(
        sandbox_provider=sandbox_provider,
    )

    context_node = create_repository_context_node(
        sandbox_provider=sandbox_provider,
    )

    # Agent nodes.
    planner_node = create_planner_node(planner_agent)
    if mcp_research_service is None:
    # Preserve compatibility with existing tests and callers.
        researcher_node = create_researcher_node(researcher_agent)
    else:
        researcher_node = create_researcher_node(
            researcher_agent,
            mcp_research_service=mcp_research_service,
            mcp_max_tool_calls=mcp_max_tool_calls,
        )
    coder_node = create_coder_node(coder_agent)
    reviewer_node = create_reviewer_node(reviewer_agent)

    if approval_pipeline_enabled:
        assert session_factory is not None
        assert patch_preparation_service is not None
        assert execution_worker_factory is not None
        patch_preparation_node = create_patch_preparation_node(
            patch_preparation_service
        )
        approval_node = create_approval_node(session_factory)
        human_approval_node = create_human_approval_node(session_factory)
        execution_record_node = create_execution_record_node(session_factory)
        approved_patch_execution_node = create_approved_patch_execution_node(
            session_factory=session_factory,
            worker_factory=execution_worker_factory,
        )

    # Review routing closure.
    def review_router(state: ForgeAgentState):
        return route_after_review(
            state,
            max_coding_attempts=max_coding_attempts,
        )

    # Explicit terminal node for retry exhaustion.
    def review_limit_reached_node(state: ForgeAgentState) -> dict:
        return {
            "status": "review_attempts_exhausted",
            "error": (
                f"Maximum coding attempts ({max_coding_attempts}) reached. "
                "The reviewer has not approved the proposed changes."
            ),
        }

    # Register infrastructure nodes.
    builder.add_node("prepare_task", trace_graph_node("prepare_task", prepare_task_node))
    builder.add_node("create_sandbox", trace_graph_node("create_sandbox", sandbox_node))
    builder.add_node("clone_repository", trace_graph_node("clone_repository", clone_node))
    builder.add_node("inspect_repository", trace_graph_node("inspect_repository", inspection_node))
    builder.add_node("build_repository_context", trace_graph_node("build_repository_context", context_node))

    # Register agent nodes.
    builder.add_node("planner", trace_graph_node("planner", planner_node))
    builder.add_node("researcher", trace_graph_node("researcher", researcher_node))
    builder.add_node("coder", trace_graph_node("coder", coder_node))
    builder.add_node("reviewer", trace_graph_node("reviewer", reviewer_node))

    if approval_pipeline_enabled:
        builder.add_node("prepare_patch", trace_graph_node("prepare_patch", patch_preparation_node))
        builder.add_node("create_approval", trace_graph_node("create_approval", approval_node))
        builder.add_node("human_approval", trace_graph_node("human_approval", human_approval_node))
        builder.add_node("create_execution", trace_graph_node("create_execution", execution_record_node))
        builder.add_node("execute_approved_patch", trace_graph_node("execute_approved_patch", approved_patch_execution_node))

    # Register terminal node.
    builder.add_node(
        "review_limit_reached",
        trace_graph_node("review_limit_reached", review_limit_reached_node),
    )

    # Entry point.
    builder.add_edge(START, "prepare_task")

    # Prepare task -> Create sandbox.
    builder.add_conditional_edges(
        "prepare_task",
        route_after_prepare,
        {
            "continue": "create_sandbox",
            "stop": END,
        },
    )

    # Create sandbox -> Clone repository.
    builder.add_conditional_edges(
        "create_sandbox",
        route_after_sandbox_creation,
        {
            "continue": "clone_repository",
            "stop": END,
        },
    )

    # Clone repository -> Inspect repository.
    builder.add_conditional_edges(
        "clone_repository",
        route_after_clone,
        {
            "continue": "inspect_repository",
            "stop": END,
        },
    )

    # Inspect repository -> Build context.
    builder.add_conditional_edges(
        "inspect_repository",
        route_after_inspection,
        {
            "continue": "build_repository_context",
            "stop": END,
        },
    )

    # Build context -> Planner.
    builder.add_conditional_edges(
        "build_repository_context",
        route_after_context_build,
        {
            "continue": "planner",
            "stop": END,
        },
    )

    # Planner -> Researcher.
    builder.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "continue": "researcher",
            "stop": END,
        },
    )

    # Researcher -> Coder.
    builder.add_conditional_edges(
        "researcher",
        route_after_research,
        {
            "continue": "coder",
            "stop": END,
        },
    )

    # Coder -> Reviewer.
    builder.add_conditional_edges(
        "coder",
        route_after_coding,
        {
            "continue": "reviewer",
            "stop": END,
        },
    )

    # Reviewer -> patch approval workflow, revision, rejection, or termination.
    if approval_pipeline_enabled:
        builder.add_conditional_edges(
            "reviewer",
            review_router,
            {
                "approved": "prepare_patch",
                "changes_requested": "coder",
                "rejected": END,
                "retry_limit_reached": "review_limit_reached",
                "stop": END,
            },
        )
        builder.add_conditional_edges(
            "prepare_patch",
            route_after_patch_preparation,
            {"continue": "create_approval", "stop": END},
        )
        builder.add_edge("create_approval", "human_approval")
        builder.add_conditional_edges(
            "human_approval",
            route_after_human_approval,
            {
                "approved": "create_execution",
                "rejected": END,
                "stop": END,
            },
        )
        builder.add_conditional_edges(
            "create_execution",
            route_after_execution_creation,
            {"continue": "execute_approved_patch", "stop": END},
        )
        builder.add_edge("execute_approved_patch", END)
    else:
        # Preserve the non-approval graph mode used by isolated agent tests.
        builder.add_conditional_edges(
            "reviewer",
            review_router,
            {
                "approved": END,
                "changes_requested": "coder",
                "rejected": END,
                "retry_limit_reached": "review_limit_reached",
                "stop": END,
            },
        )

    # Retry exhaustion -> End.
    builder.add_edge("review_limit_reached", END)

    return builder.compile(checkpointer=checkpointer)
