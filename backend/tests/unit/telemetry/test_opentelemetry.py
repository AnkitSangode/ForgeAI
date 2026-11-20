from forgeai.telemetry.opentelemetry import trace_graph_node


def test_trace_graph_node_preserves_node_result():
    def node(state):
        return {"status": "completed", "task_id": state["task_id"]}

    traced = trace_graph_node("planner", node)
    result = traced({"task_id": "task-123", "agent_run_id": "run-123"})

    assert result == {"status": "completed", "task_id": "task-123"}


def test_trace_graph_node_reraises_node_exception():
    def node(_state):
        raise RuntimeError("node failed")

    traced = trace_graph_node("coder", node)

    try:
        traced({"task_id": "task-123"})
    except RuntimeError as exc:
        assert str(exc) == "node failed"
    else:
        raise AssertionError("Expected node exception to be re-raised")


import asyncio


def test_trace_graph_node_supports_async_nodes():
    async def node(state):
        return {"status": "completed", "task_id": state["task_id"]}

    traced = trace_graph_node("researcher", node)
    result = asyncio.run(traced({"task_id": "task-async"}))

    assert result["status"] == "completed"
    assert result["task_id"] == "task-async"
