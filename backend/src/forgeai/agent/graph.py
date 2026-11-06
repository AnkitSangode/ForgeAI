
from typing import Literal

from langgraph.graph import END, START, StateGraph

from forgeai.agent.coder import CoderAgent
from forgeai.agent.nodes import (
    create_coder_node,
    create_planner_node,
    create_researcher_node,
    create_repository_clone_node,
    create_repository_context_node,
    create_repository_inspection_node,
    create_reviewer_node,
    prepare_task_node,
)
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.reviewer import ReviewerAgent
from forgeai.agent.reviewer_schema import ReviewResponse
from forgeai.agent.sandbox_nodes import create_sandbox_node
from forgeai.agent.state import ForgeAgentState
from forgeai.execution.sandbox.base import SandboxProvider


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

    if not state.get("sandbox_session"):
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
) -> Literal[
    "approved",
    "changes_requested",
    "rejected",
    "stop",
]:
    if state.get("status") == "failed":
        return "stop"

    review_data = state.get("review")

    if not review_data:
        return "stop"

    review = ReviewResponse.model_validate(review_data)

    if review.decision == "approved":
        return "approved"

    if review.decision == "changes_requested":
        return "changes_requested"

    return "rejected"


def build_agent_graph(
    planner_agent: PlannerAgent,
    researcher_agent: ResearcherAgent,
    coder_agent: CoderAgent,
    reviewer_agent: ReviewerAgent,
    sandbox_provider: SandboxProvider,
    sandbox_timeout_seconds: int = 600,
):
    """Build and compile the ForgeAI agent workflow."""

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
    researcher_node = create_researcher_node(researcher_agent)
    coder_node = create_coder_node(coder_agent)
    reviewer_node = create_reviewer_node(reviewer_agent)

    # Register nodes.
    builder.add_node("prepare_task", prepare_task_node)
    builder.add_node("create_sandbox", sandbox_node)
    builder.add_node("clone_repository", clone_node)
    builder.add_node("inspect_repository", inspection_node)
    builder.add_node("build_repository_context", context_node)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("coder", coder_node)
    builder.add_node("reviewer", reviewer_node)

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

    # Reviewer -> End (temporary until HITL integration).
    builder.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "approved": END,
            "changes_requested": END,
            "rejected": END,
            "stop": END,
        },
    )

    return builder.compile()
