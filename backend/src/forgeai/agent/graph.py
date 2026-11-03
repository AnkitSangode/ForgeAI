from typing import Literal

from langgraph.graph import END, START, StateGraph

from forgeai.agent.nodes import (
    build_repository_context_node,
    create_planner_node,
    create_researcher_node,
    inspect_repostiory_node,
    prepare_task_node,
)
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.state import ForgeAgentState


def route_after_prepare(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    if state.get("status") == "failed":
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


def build_agent_graph(
    planner_agent: PlannerAgent,
    researcher_agent: ResearcherAgent,
):
    """Build and compile the ForgeAI agent workflow."""

    builder = StateGraph(ForgeAgentState)

    planner_node = create_planner_node(planner_agent)
    researcher_node = create_researcher_node(researcher_agent)

    # Register nodes
    builder.add_node("prepare_task", prepare_task_node)
    builder.add_node("inspect_repository", inspect_repostiory_node)
    builder.add_node(
        "build_repository_context",
        build_repository_context_node,
    )
    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)

    # Entry point
    builder.add_edge(START, "prepare_task")

    # Prepare task routing
    builder.add_conditional_edges(
        "prepare_task",
        route_after_prepare,
        {
            "continue": "inspect_repository",
            "stop": END,
        },
    )

    # Repository inspection routing
    builder.add_conditional_edges(
        "inspect_repository",
        route_after_inspection,
        {
            "continue": "build_repository_context",
            "stop": END,
        },
    )

    # Repository context routing
    builder.add_conditional_edges(
        "build_repository_context",
        route_after_context_build,
        {
            "continue": "planner",
            "stop": END,
        },
    )

    # Planner routing
    builder.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "continue": "researcher",
            "stop": END,
        },
    )

    # Researcher completes the current workflow
    builder.add_edge("researcher", END)

    return builder.compile()
