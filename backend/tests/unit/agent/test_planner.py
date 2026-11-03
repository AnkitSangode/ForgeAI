from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from forgeai.agent.planner import PlannerAgent
from forgeai.agent.schemas import PlanResponse, PlanStep
from forgeai.llm.exceptions import LLMResponseError
from forgeai.llm.schemas import LLMResponse


@pytest.fixture
def mock_llm_service():
    """Create a fake LLM service."""
    return MagicMock()


@pytest.fixture
def planner(mock_llm_service):
    """Create a PlannerAgent with the fake LLM service."""
    return PlannerAgent(llm_service=mock_llm_service)


@pytest.fixture
def valid_plan():
    """Provide a valid structured plan for testing."""
    return PlanResponse(
        objective="Fix the authentication session issue.",
        steps=[
            PlanStep(
                step_number=1,
                title="Inspect authentication flow",
                description="Identify login and session handling implementation.",
                expected_output="Relevant authentication files.",
            ),
            PlanStep(
                step_number=2,
                title="Investigate session persistence",
                description="Examine cookie settings and session storage.",
                expected_output="Evidence about the session failure.",
            ),
        ],
        success_criteria=[
            "Users remain authenticated after successful login.",
            "Existing authentication tests pass.",
        ],
    )


def test_generate_plan_returns_structured_plan(
    planner,
    mock_llm_service,
    valid_plan,
):
    # Arrange: configure the fake LLM response.
    mock_llm_service.generate.return_value = LLMResponse(
        content=valid_plan,
        model="test-model",
    )

    # Act: ask the Planner to generate a plan.
    result = planner.generate_plan(
        task_description="Fix the authentication session issue.",
        repository_context="The project uses FastAPI and JWT authentication.",
    )

    # Assert: verify the returned result.
    assert result == valid_plan
    assert isinstance(result, PlanResponse)


def test_generate_plan_requests_correct_response_schema(
    planner,
    mock_llm_service,
    valid_plan,
):
    mock_llm_service.generate.return_value = LLMResponse(
        content=valid_plan,
        model="test-model",
    )

    planner.generate_plan(
        task_description="Fix the authentication session issue.",
        repository_context="Authentication uses JWT.",
    )

    # Verify that Planner requested structured PlanResponse output.
    mock_llm_service.generate.assert_called_once()

    call_arguments = mock_llm_service.generate.call_args

    assert call_arguments.kwargs["response_schema"] is PlanResponse


def test_generate_plan_rejects_empty_task(planner):
    with pytest.raises(ValueError, match="Task description cannot be empty"):
        planner.generate_plan(
            task_description="   ",
            repository_context="Some repository context.",
        )


def test_generate_plan_rejects_invalid_llm_response(
    planner,
    mock_llm_service,
):
    mock_llm_service.generate.return_value = LLMResponse(
        content="This is plain text, not a structured plan.",
        model="test-model",
    )

    with pytest.raises(
        LLMResponseError,
        match="Planner received an invalid structured response",
    ):
        planner.generate_plan(
            task_description="Fix the authentication session issue.",
            repository_context="Authentication uses JWT.",
        )


def test_generate_plan_handles_empty_repository_context(
    planner,
    mock_llm_service,
    valid_plan,
):
    mock_llm_service.generate.return_value = LLMResponse(
        content=valid_plan,
        model="test-model",
    )

    planner.generate_plan(
        task_description="Fix the authentication session issue.",
        repository_context="   ",
    )

    # Inspect the prompt sent to the LLM service.
    call_arguments = mock_llm_service.generate.call_args
    prompt = call_arguments.kwargs["prompt"]

    assert "No repository context is available." in prompt


def test_plan_response_rejects_non_sequential_step_numbers():
    with pytest.raises(ValidationError):
        PlanResponse(
            objective="Fix the authentication bug in the API.",
            steps=[
                {
                    "step_number": 1,
                    "title": "Inspect authentication",
                    "description": "Inspect the authentication flow and identify the failure.",
                    "expected_output": "A clear understanding of the authentication flow.",
                },
                {
                    "step_number": 3,  # Invalid: expected 2
                    "title": "Fix authentication",
                    "description": "Implement the required authentication correction.",
                    "expected_output": "Corrected authentication behavior.",
                },
            ],
            success_criteria=[
                "Authentication succeeds with valid credentials.",
                "Invalid credentials are rejected.",
            ],
        )


def test_plan_response_rejects_empty_success_criteria():
    with pytest.raises(ValidationError):
        PlanResponse(
            objective="Fix the authentication bug in the API.",
            steps=[
                {
                    "step_number": 1,
                    "title": "Inspect authentication",
                    "description": "Inspect the authentication flow and identify the failure.",
                    "expected_output": "A clear understanding of the authentication flow.",
                },
            ],
            success_criteria=[
                "Authentication succeeds with valid credentials.",
                "   ",  # Invalid: whitespace-only criterion
            ],
        )
