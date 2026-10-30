
from typing import Literal

from langgraph.graph import END, START, StateGraph

from forgeai.agent.nodes import (
    create_initial_plan_node,
    prepare_task_node,
)
from forgeai.agent.state import ForgeAgentState


def route_after_prepare(
    state: ForgeAgentState,
) -> Literal["continue", "stop"]:
    """Decide whether the workflow should continue or terminate."""

    if state.get("status") == "failed":
        return "stop"

    return "continue"


def build_agent_graph():
    """Build and compile the initial ForgeAI workflow."""

    builder = StateGraph(ForgeAgentState)

    # Register nodes.
    builder.add_node("prepare_task", prepare_task_node)
    builder.add_node("create_initial_plan", create_initial_plan_node)

    # Define the entry point.
    builder.add_edge(START, "prepare_task")

    # Route execution based on the task preparation result.
    builder.add_conditional_edges(
        "prepare_task",
        route_after_prepare,
        {
            "continue": "create_initial_plan",
            "stop": END,
        },
    )

    # Finish after planning.
    builder.add_edge("create_initial_plan", END)

    return builder.compile()


agent_graph = build_agent_graph()




