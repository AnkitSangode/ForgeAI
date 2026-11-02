from typing import TypeVar

from pydantic import BaseModel

from forgeai.llm.base import LLMProvider
from forgeai.llm.schemas import LLMResponse

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Application service for LLM interactions."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
    ) -> LLMResponse:
        """Generate a response through the configured provider."""

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        return self._provider.generate(
            prompt=prompt,
            response_schema=response_schema,
        )
