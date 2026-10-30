
from forgeai.agent.graph import agent_graph


def test_graph_creates_initial_plan():
    initial_state = {
        "task_id": "task-001",
        "task_description": "Fix the failing login tests",
        "repository_url": "https://github.com/example/repo",
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "plan_created"
    assert result["task_id"] == "task-001"
    assert "Target repository:" in result["repository_context"]


def test_graph_stops_when_task_description_is_empty():
    initial_state = {
        "task_id": "task-002",
        "task_description": "   ",
        "repository_url": "https://github.com/example/repo",
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["error"] == "Task description cannot be empty."

    # The planning node must not execute.
    assert "plan" not in result


def test_graph_stops_when_repository_url_is_empty():
    initial_state = {
        "task_id": "task-003",
        "task_description": "Fix the failing login tests",
        "repository_url": "   ",
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["error"] == "Repository URL cannot be empty."

    # The planning node must not execute.
    assert "plan" not in result
