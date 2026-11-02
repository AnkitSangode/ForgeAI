from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from forgeai.llm.llm_service import LLMService
from forgeai.llm.schemas import LLMResponse


class PlanResponse(BaseModel):
    steps: list[str]


@pytest.fixture
def mock_provider():
    """Create a mock provider for isolated service testing."""
    return Mock()


@pytest.fixture
def llm_service(mock_provider):
    """Inject the mock provider into LLMService."""
    return LLMService(provider=mock_provider)


def test_generate_plain_text(llm_service, mock_provider):
    expected = LLMResponse(
        content="Inspect authentication.py",
        model="test-model",
        input_tokens=100,
        output_tokens=20,
    )
    mock_provider.generate.return_value = expected

    result = llm_service.generate("Investigate authentication bug")

    assert result is expected
    mock_provider.generate.assert_called_once_with(
        prompt="Investigate authentication bug",
        response_schema=None,
    )


def test_generate_structured_response(llm_service, mock_provider):
    plan = PlanResponse(
        steps=["Inspect repository", "Identify root cause"],
    )

    expected = LLMResponse(
        content=plan,
        model="test-model",
        input_tokens=120,
        output_tokens=40,
    )
    mock_provider.generate.return_value = expected

    result = llm_service.generate(
        prompt="Create an investigation plan",
        response_schema=PlanResponse,
    )

    assert result.content == plan
    mock_provider.generate.assert_called_once_with(
        prompt="Create an investigation plan",
        response_schema=PlanResponse,
    )


@pytest.mark.parametrize("prompt", ["", "   ", "\n\t"])
def test_generate_rejects_empty_prompt(llm_service, mock_provider, prompt):
    with pytest.raises(ValueError, match="Prompt cannot be empty."):
        llm_service.generate(prompt)

    mock_provider.generate.assert_not_called()


def test_generate_propagates_provider_failure(llm_service, mock_provider):
    mock_provider.generate.side_effect = RuntimeError("Provider unavailable.")

    with pytest.raises(RuntimeError, match="Provider unavailable."):
        llm_service.generate("Investigate authentication bug")
