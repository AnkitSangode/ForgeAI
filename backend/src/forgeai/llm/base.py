
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

from forgeai.llm.schemas import LLMResponse
from forgeai.llm.tool_schemas import (
    LLMMessage,
    LLMToolCallResponse,
    LLMToolDefinition,
)

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Contract for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
    ) -> LLMResponse:
        """Generate response from the configured LLM provider."""
        raise NotImplementedError

    def generate_with_tools(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolDefinition],
    ) -> LLMToolCallResponse:
        """Generate a response that may contain tool-call requests.

        Providers that do not support native tool calling must override
        this method before they can be used for MCP orchestration.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support tool calling."
        )
