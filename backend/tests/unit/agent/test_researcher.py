from unittest.mock import MagicMock

import pytest

from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.schemas import PlanResponse
from forgeai.llm.exceptions import LLMResponseError


@pytest.fixture
def mock_llm_service():
    return MagicMock()


@pytest.fixture
def researcher(mock_llm_service):
    return ResearcherAgent(llm_service=mock_llm_service)


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
def repository_files():
    return [
        {
            "file_path": "src/auth.py",
            "content": (
                "def login(username, password):\n"
                "    user = authenticate(username, password)\n"
                "    return user\n"
            ),
        }
    ]


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
        remaining_questions=["How does the authenticate function handle invalid credentials?"],
    )


def test_researcher_returns_structured_research(
    researcher,
    mock_llm_service,
    valid_plan,
    repository_files,
    valid_research,
):
    mock_llm_service.generate.return_value.content = valid_research

    result = researcher.research(
        task_description="Investigate the login failure.",
        plan=valid_plan,
        repository_context_files=repository_files,
    )

    assert result == valid_research
    assert result.files_inspected == ["src/auth.py"]


def test_researcher_passes_research_response_schema(
    researcher,
    mock_llm_service,
    valid_plan,
    repository_files,
    valid_research,
):
    mock_llm_service.generate.return_value.content = valid_research

    researcher.research(
        task_description="Investigate the login failure.",
        plan=valid_plan,
        repository_context_files=repository_files,
    )

    _, kwargs = mock_llm_service.generate.call_args

    assert kwargs["response_schema"] is ResearchResponse


def test_researcher_rejects_empty_task_description(
    researcher,
    valid_plan,
    repository_files,
):
    with pytest.raises(ValueError, match="Task description"):
        researcher.research(
            task_description="   ",
            plan=valid_plan,
            repository_context_files=repository_files,
        )


def test_researcher_rejects_empty_repository_context(
    researcher,
    valid_plan,
):
    with pytest.raises(ValueError, match="Repository context"):
        researcher.research(
            task_description="Investigate the login failure.",
            plan=valid_plan,
            repository_context_files=[],
        )


def test_researcher_rejects_invalid_llm_response(
    researcher,
    mock_llm_service,
    valid_plan,
    repository_files,
):
    mock_llm_service.generate.return_value.content = "Invalid response"

    with pytest.raises(LLMResponseError, match="invalid structured response"):
        researcher.research(
            task_description="Investigate the login failure.",
            plan=valid_plan,
            repository_context_files=repository_files,
        )


def test_researcher_rejects_unavailable_file_reference(
    researcher,
    mock_llm_service,
    valid_plan,
    repository_files,
    valid_research,
):
    invalid_research = valid_research.model_copy(update={"files_inspected": ["src/missing.py"]})
    mock_llm_service.generate.return_value.content = invalid_research

    with pytest.raises(LLMResponseError, match="unavailable file"):
        researcher.research(
            task_description="Investigate the login failure.",
            plan=valid_plan,
            repository_context_files=repository_files,
        )


def test_researcher_rejects_fabricated_evidence(
    researcher,
    mock_llm_service,
    valid_plan,
    repository_files,
    valid_research,
):
    invalid_finding = valid_research.findings[0].model_copy(
        update={"evidence": "raise Exception('fabricated evidence')"}
    )

    invalid_research = valid_research.model_copy(update={"findings": [invalid_finding]})

    mock_llm_service.generate.return_value.content = invalid_research

    with pytest.raises(LLMResponseError, match="does not match"):
        researcher.research(
            task_description="Investigate the login failure.",
            plan=valid_plan,
            repository_context_files=repository_files,
        )


def test_researcher_rejects_duplicate_repository_paths(
    researcher,
    valid_plan,
    repository_files,
):
    duplicate_files = repository_files + repository_files

    with pytest.raises(ValueError, match="Duplicate"):
        researcher.research(
            task_description="Investigate the login failure.",
            plan=valid_plan,
            repository_context_files=duplicate_files,
        )
