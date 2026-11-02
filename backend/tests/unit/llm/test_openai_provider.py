from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, SecretStr

from forgeai.core.config import Settings
from forgeai.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from forgeai.llm.openai_provider import OpenAIProvider
from forgeai.llm.schemas import LLMResponse


class ResearchFinding(BaseModel):
    root_cause: str
    confidence: float


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key=SecretStr("test-api-key"),
        openai_model="gpt-4.1",
        openai_temperature=0.0,
        openai_timeout=60.0,
        openai_max_retries=2,
    )


@pytest.fixture
def mock_llm(monkeypatch):
    """Replace ChatOpenAI with a mock to avoid real API calls."""

    llm_instance = MagicMock()

    chat_openai_mock = MagicMock(return_value=llm_instance)

    monkeypatch.setattr(
        "forgeai.llm.openai_provider.ChatOpenAI",
        chat_openai_mock,
    )

    return llm_instance, chat_openai_mock


def create_openai_error(error_type):
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
    )

    if error_type is APITimeoutError:
        return APITimeoutError(request=request)

    if error_type is APIConnectionError:
        return APIConnectionError(
            message="Connection failed.",
            request=request,
        )

    if error_type is AuthenticationError:
        response = httpx.Response(401, request=request)
        return AuthenticationError(
            message="Invalid API key.",
            response=response,
            body=None,
        )

    if error_type is RateLimitError:
        response = httpx.Response(429, request=request)
        return RateLimitError(
            message="Rate limit exceeded.",
            response=response,
            body=None,
        )

    if error_type is APIStatusError:
        response = httpx.Response(500, request=request)
        return APIStatusError(
            message="Internal server error.",
            response=response,
            body=None,
        )

    raise ValueError("Unsupported error type.")


def test_generate_plain_text_response(settings, mock_llm):
    llm_instance, _ = mock_llm

    llm_instance.invoke.return_value = SimpleNamespace(
        content="Inspect the authentication module.",
        usage_metadata={
            "input_tokens": 100,
            "output_tokens": 20,
        },
        response_metadata={
            "model_name": "gpt-4.1",
        },
    )

    provider = OpenAIProvider(settings)

    response = provider.generate(
        prompt="Investigate the authentication bug.",
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Inspect the authentication module."
    assert response.model == "gpt-4.1"
    assert response.input_tokens == 100
    assert response.output_tokens == 20


def test_generate_structured_response(settings, mock_llm):
    llm_instance, _ = mock_llm

    finding = ResearchFinding(
        root_cause="Incorrect exception handling.",
        confidence=0.95,
    )

    raw_message = SimpleNamespace(
        usage_metadata={
            "input_tokens": 150,
            "output_tokens": 50,
        },
        response_metadata={
            "model_name": "gpt-4.1",
        },
    )

    llm_instance.with_structured_output.return_value.invoke.return_value = {
        "raw": raw_message,
        "parsed": finding,
        "parsing_error": None,
    }

    provider = OpenAIProvider(settings)

    response = provider.generate(
        prompt="Investigate the authentication bug.",
        response_schema=ResearchFinding,
    )

    assert isinstance(response, LLMResponse)
    assert isinstance(response.content, ResearchFinding)
    assert response.content.root_cause == "Incorrect exception handling."
    assert response.content.confidence == 0.95
    assert response.input_tokens == 150
    assert response.output_tokens == 50


def test_generate_response_without_usage_metadata(settings, mock_llm):
    llm_instance, _ = mock_llm

    llm_instance.invoke.return_value = SimpleNamespace(
        content="Authentication investigation completed.",
        usage_metadata=None,
        response_metadata={
            "model_name": "gpt-4.1",
        },
    )

    provider = OpenAIProvider(settings)

    response = provider.generate(
        prompt="Investigate authentication.",
    )

    assert response.content == "Authentication investigation completed."
    assert response.input_tokens is None
    assert response.output_tokens is None


def test_generate_structured_response_with_parsing_error(
    settings,
    mock_llm,
):
    llm_instance, _ = mock_llm

    llm_instance.with_structured_output.return_value.invoke.return_value = {
        "raw": SimpleNamespace(),
        "parsed": None,
        "parsing_error": ValueError("Invalid structured output."),
    }

    provider = OpenAIProvider(settings)

    with pytest.raises(
        LLMResponseError,
        match="Unable to parse structured LLM response.",
    ):
        provider.generate(
            prompt="Create a research finding.",
            response_schema=ResearchFinding,
        )


def test_generate_structured_response_with_empty_result(
    settings,
    mock_llm,
):
    llm_instance, _ = mock_llm

    llm_instance.with_structured_output.return_value.invoke.return_value = {
        "raw": SimpleNamespace(),
        "parsed": None,
        "parsing_error": None,
    }

    provider = OpenAIProvider(settings)

    with pytest.raises(
        LLMResponseError,
        match="LLM returned an empty structured response.",
    ):
        provider.generate(
            prompt="Create a research finding.",
            response_schema=ResearchFinding,
        )


@pytest.mark.parametrize(
    ("openai_error", "expected_error"),
    [
        (AuthenticationError, LLMAuthenticationError),
        (RateLimitError, LLMRateLimitError),
        (APITimeoutError, LLMTimeoutError),
        (APIConnectionError, LLMConnectionError),
        (APIStatusError, LLMProviderError),
    ],
)
def test_generate_normalizes_openai_exceptions(
    settings,
    mock_llm,
    openai_error,
    expected_error,
):
    llm_instance, _ = mock_llm

    llm_instance.invoke.side_effect = create_openai_error(openai_error)

    provider = OpenAIProvider(settings)

    with pytest.raises(expected_error):
        provider.generate(
            prompt="Investigate the authentication bug.",
        )


def test_generate_normalizes_unexpected_exceptions(
    settings,
    mock_llm,
):
    llm_instance, _ = mock_llm

    llm_instance.invoke.side_effect = RuntimeError("Unexpected internal error.")

    provider = OpenAIProvider(settings)

    with pytest.raises(RuntimeError, match="Unexpected internal error."):
        provider.generate(
            prompt="Investigate the authentication bug.",
        )

def test_generate_does_not_normalize_programming_errors(
    settings,
    mock_llm,
):
    llm_instance, _ = mock_llm

    llm_instance.invoke.side_effect = AttributeError(
        "Unexpected attribute access."
    )

    provider = OpenAIProvider(settings)

    with pytest.raises(
        AttributeError,
        match="Unexpected attribute access.",
    ):
        provider.generate(
            prompt="Investigate the authentication bug.",
        )