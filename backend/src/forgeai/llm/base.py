from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from forgeai.llm.schemas import LLMResponse

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
