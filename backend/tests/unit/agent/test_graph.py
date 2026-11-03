from unittest.mock import Mock

import pytest

from forgeai.agent.coder import CoderAgent
from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.agent.graph import build_agent_graph
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.schemas import PlanResponse, PlanStep


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
def planner_agent():
    agent = Mock(spec=PlannerAgent)

    agent.generate_plan.return_value = PlanResponse(
        objective="Fix the authentication bug.",
        steps=[
            PlanStep(
                step_number=1,
                title="Inspect authentication",
                description="Inspect the authentication implementation.",
                expected_output="Identify the authentication problem.",
            )
        ],
        success_criteria=["Authentication works correctly."],
    )

    return agent


@pytest.fixture
def researcher_agent():
    agent = Mock(spec=ResearcherAgent)

    agent.research.return_value = {
        "summary": "Authentication implementation needs correction.",
        "findings": [],
    }

    # Replace with a real ResearchResponse, as shown below.
    return agent


@pytest.fixture
def valid_research_response():

    return ResearchResponse(
        summary="Found an authentication issue in the repository.",
        findings=[
            ResearchFinding(
                file_path="README.md",
                evidence="# Example Project",
                observation="The README contains project information.",
                relevance="It is the only available repository context.",
            )
        ],
        files_inspected=["README.md"],
        root_cause_hypothesis=("The authentication implementation requires further inspection."),
        confidence="low",
        remaining_questions=[],
    )


@pytest.fixture
def coder_agent():
    agent = Mock(spec=CoderAgent)

    agent.generate_changes.return_value = CoderResponse(
        summary="Update authentication documentation.",
        changes=[
            CodeChange(
                file_path="README.md",
                change_type="modify",
                unified_diff=(
                    "--- a/README.md\n"
                    "+++ b/README.md\n"
                    "@@ -1 +1 @@\n"
                    "-# Example Project\n"
                    "+# Example Project\n"
                ),
                explanation="Update the project documentation.",
            )
        ],
        tests_to_run=[],
        risks=[],
    )

    return agent


def test_graph_executes_successful_workflow(
    valid_initial_state,
    planner_agent,
    researcher_agent,
    valid_research_response,
    coder_agent,
):
    researcher_agent.research.return_value = valid_research_response

    graph = build_agent_graph(
        planner_agent=planner_agent,
        researcher_agent=researcher_agent,
        coder_agent=coder_agent,
    )

    result = graph.invoke(valid_initial_state)

    assert result["status"] == "code_changes_generated"
    assert result["plan"]["objective"] == "Fix the authentication bug."
    assert result["research"]["summary"] == ("Found an authentication issue in the repository.")
    assert result["code_changes"]["summary"] == ("Update authentication documentation.")

    planner_agent.generate_plan.assert_called_once()
    researcher_agent.research.assert_called_once()
    coder_agent.generate_changes.assert_called_once()


def test_graph_skips_researcher_when_planner_fails(
    valid_initial_state,
    planner_agent,
    researcher_agent,
    coder_agent,
):
    from forgeai.llm.exceptions import LLMProviderError

    planner_agent.generate_plan.side_effect = LLMProviderError("LLM provider unavailable.")

    graph = build_agent_graph(
        planner_agent=planner_agent,
        researcher_agent=researcher_agent,
        coder_agent=coder_agent,
    )

    result = graph.invoke(valid_initial_state)

    assert result["status"] == "failed"
    researcher_agent.research.assert_not_called()
    coder_agent.generate_changes.assert_not_called()


def test_graph_skips_coder_when_researcher_fails(
    valid_initial_state,
    planner_agent,
    researcher_agent,
    coder_agent,
):
    from forgeai.llm.exceptions import LLMProviderError

    researcher_agent.research.side_effect = LLMProviderError("Research failed.")

    graph = build_agent_graph(
        planner_agent=planner_agent,
        researcher_agent=researcher_agent,
        coder_agent=coder_agent,
    )

    result = graph.invoke(valid_initial_state)

    assert result["status"] == "failed"
    coder_agent.generate_changes.assert_not_called()
