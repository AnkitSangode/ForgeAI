from unittest.mock import MagicMock

import pytest

from forgeai.agent.nodes import create_researcher_node
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.schemas import PlanResponse
from forgeai.llm.exceptions import LLMConnectionError


@pytest.fixture
def mock_researcher_agent():
    return MagicMock()


@pytest.fixture
def researcher_node(mock_researcher_agent):
    return create_researcher_node(mock_researcher_agent)


@pytest.fixture
def valid_plan():
    return PlanResponse(
        objective="Investigate the authentication failure.",
        steps=[
            {
                "step_number": 1,
                "title": "Inspect authentication",
                "description": "Inspect the authentication endpoint and service.",
                "expected_output": "Authentication flow findings.",
            }
        ],
        success_criteria=["Identify the cause of the authentication failure."],
    )


@pytest.fixture
def valid_research():
    return ResearchResponse(
        summary="The login function delegates authentication to another function.",
        findings=[
            ResearchFinding(
                file_path="src/auth.py",
                evidence="user = authenticate(username, password)",
                observation="The login function delegates credential verification.",
                relevance="The delegated function is relevant to the reported login failure.",
            )
        ],
        files_inspected=["src/auth.py"],
        root_cause_hypothesis=(
            "The authentication failure may originate in the delegated "
            "credential verification function."
        ),
        confidence="medium",
        remaining_questions=[],
    )


@pytest.fixture
def valid_state(valid_plan):
    return {
        "task_id": "task-123",
        "task_description": "Investigate the login failure.",
        "repository_url": "https://github.com/example/repository",
        "repository_context_files": [
            {
                "file_path": "src/auth.py",
                "content": "user = authenticate(username, password)",
            }
        ],
        "plan": valid_plan.model_dump(mode="json"),
        "status": "plan_created",
    }


def test_researcher_node_stores_research(
    researcher_node,
    mock_researcher_agent,
    valid_state,
    valid_plan,
    valid_research,
):
    mock_researcher_agent.research.return_value = valid_research

    result = researcher_node(valid_state)

    assert result["status"] == "research_completed"
    assert result["research"] == valid_research.model_dump(mode="json")
    assert result["error"] == ""

    mock_researcher_agent.research.assert_called_once_with(
        task_description=valid_state["task_description"],
        plan=valid_plan,
        repository_context_files=valid_state["repository_context_files"],
    )


def test_researcher_node_skips_failed_workflow(
    researcher_node,
    mock_researcher_agent,
    valid_state,
):
    valid_state["status"] = "failed"

    result = researcher_node(valid_state)

    assert result == {}
    mock_researcher_agent.research.assert_not_called()


def test_researcher_node_fails_when_plan_is_missing(
    researcher_node,
    mock_researcher_agent,
    valid_state,
):
    valid_state.pop("plan")

    result = researcher_node(valid_state)

    assert result["status"] == "failed"
    assert "no plan" in result["error"].lower()
    mock_researcher_agent.research.assert_not_called()


def test_researcher_node_fails_when_repository_context_is_missing(
    researcher_node,
    mock_researcher_agent,
    valid_state,
):
    valid_state["repository_context_files"] = []

    result = researcher_node(valid_state)

    assert result["status"] == "failed"
    assert "repository context" in result["error"].lower()
    mock_researcher_agent.research.assert_not_called()


def test_researcher_node_handles_llm_error(
    researcher_node,
    mock_researcher_agent,
    valid_state,
):
    mock_researcher_agent.research.side_effect = LLMConnectionError("LLM connection failed.")

    result = researcher_node(valid_state)

    assert result["status"] == "failed"
    assert "LLM connection failed" in result["error"]


def test_researcher_node_rejects_invalid_plan(
    researcher_node,
    mock_researcher_agent,
    valid_state,
):
    valid_state["plan"] = {"invalid": "plan"}

    result = researcher_node(valid_state)

    assert result["status"] == "failed"
    mock_researcher_agent.research.assert_not_called()
