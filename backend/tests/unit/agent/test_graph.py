from unittest.mock import MagicMock

import pytest

from forgeai.agent.graph import build_agent_graph
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.schemas import PlanResponse
from forgeai.llm.exceptions import LLMConnectionError


@pytest.fixture
def valid_initial_state(tmp_path):
    readme_content = "# Example Project"

    readme_file = tmp_path / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")

    return {
        "task_id": "task-123",
        "task_description": "Fix the authentication bug.",
        "repository_url": "https://github.com/example/repository",
        "repository_path": str(tmp_path),
        "repository_context_files": [],
        "repository_context_status": "unavailable",
        "repository_context_bytes": 0,
        "repository_context_skipped_files": [],
        "repository_context_errors": [],
    }


@pytest.fixture
def mock_planner():
    planner = MagicMock()
    planner.generate_plan.return_value = PlanResponse(
        objective="Fix the authentication bug.",
        steps=[
            {
                "step_number": 1,
                "title": "Inspect implementation",
                "description": "Inspect the relevant repository implementation.",
                "expected_output": "An understanding of the implementation.",
            }
        ],
        success_criteria=["Identify the relevant implementation."],
    )
    return planner


@pytest.fixture
def mock_researcher():
    researcher = MagicMock()
    researcher.research.return_value = ResearchResponse(
        summary="The relevant implementation was inspected.",
        findings=[
            ResearchFinding(
                file_path="README.md",
                evidence="# Example Project",
                observation="The repository contains a project README.",
                relevance="The README provides basic project context.",
            )
        ],
        files_inspected=["README.md"],
        root_cause_hypothesis=(
            "There is insufficient evidence to identify a confirmed root cause."
        ),
        confidence="low",
        remaining_questions=["Which implementation file handles the task?"],
    )
    return researcher


@pytest.fixture
def agent_graph(mock_planner, mock_researcher):
    return build_agent_graph(
        planner_agent=mock_planner,
        researcher_agent=mock_researcher,
    )


def test_agent_graph_successfully_inspects_repository(
    tmp_path,
    agent_graph,
    mock_planner,
):
    # Arrange
    repository = tmp_path / "test-project"
    repository.mkdir()

    (repository / "README.md").write_text("# Test Project")
    (repository / "main.py").write_text("print('Hello')")

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    # Act
    result = agent_graph.invoke(initial_state)

    # Assert
    assert result["status"] == "research_completed"
    assert result["repository_status"] == "available"
    assert result["repository_files"]
    assert result["repository_truncated"] is False
    assert result["plan"]["objective"] == "Fix the authentication bug."
    assert "README.md" in result["repository_files"]

    mock_planner.generate_plan.assert_called_once()


def test_agent_graph_fails_when_repository_path_is_missing(agent_graph):
    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": "",
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["error"] == "Local repository path cannot be empty."
    assert "plan" not in result


def test_agent_graph_fails_when_repository_does_not_exist(
    tmp_path,
    agent_graph,
    mock_planner,
):
    repository = tmp_path / "nonexistent"

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["repository_status"] == "unavailable"
    assert result["repository_files"] == []
    assert result["error"] == "Repository path does not exist."
    assert "plan" not in result

    mock_planner.generate_plan.assert_not_called()


def test_agent_graph_preserves_repository_truncation_status(
    tmp_path,
    agent_graph,
):
    repository = tmp_path / "test-project"
    repository.mkdir()

    (repository / "README.md").write_text("# Test Project")

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["repository_truncated"] is False


def test_agent_graph_continues_with_partial_repository_context(
    tmp_path,
    agent_graph,
):
    repository = tmp_path / "test-project"
    repository.mkdir()

    oversized_content = "x" * (100 * 1024 + 1)

    (repository / "README.md").write_text(
        oversized_content,
        encoding="utf-8",
    )

    (repository / "main.py").write_text(
        "def main(): pass",
        encoding="utf-8",
    )

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["repository_context_status"] == "partial"
    assert result["status"] == "research_completed"

    assert len(result["repository_context_files"]) == 1
    assert result["repository_context_files"][0]["file_path"] == "main.py"

    assert "README.md" in result["repository_context_skipped_files"]
    assert result["plan"]["steps"]


def test_graph_executes_planner_then_researcher(
    agent_graph,
    mock_planner,
    mock_researcher,
    valid_initial_state,
):
    result = agent_graph.invoke(valid_initial_state)

    print("\n--- GRAPH RESULT ---")
    print(result)

    assert result["status"] == "research_completed"

    mock_planner.generate_plan.assert_called_once()
    mock_researcher.research.assert_called_once()


def test_graph_does_not_execute_researcher_when_planner_fails(
    agent_graph,
    mock_planner,
    mock_researcher,
    valid_initial_state,
):
    mock_planner.generate_plan.side_effect = LLMConnectionError("LLM connection failed.")

    result = agent_graph.invoke(valid_initial_state)

    assert result["status"] == "failed"
    mock_researcher.research.assert_not_called()
