from typing import TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from forgeai.core.config import Settings
from forgeai.llm.base import LLMProvider
from forgeai.llm.schemas import LLMResponse

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of the LLM provider contract."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.openai_model

        self._llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key.get_secret_value(),
            temperature=settings.openai_temperature,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )

    def generate(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
    ) -> LLMResponse:
        """Generate a plain text or structured response."""

        if response_schema is None:
            message = self._llm.invoke(prompt)
            content = message.content
        else:
            structured_llm = self._llm.with_structured_output(
                response_schema,
                include_raw=True,
            )

            result = structured_llm.invoke(prompt)

            if result["parsing_error"] is not None:
                raise ValueError("Unable to parse structured LLM response.")

            if result["parsed"] is None:
                raise ValueError("LLM returned an empty structured response.")

            message = result["raw"]
            content = result["parsed"]

        usage = getattr(message, "usage_metadata", None) or {}
        response_metadata = getattr(message, "response_metadata", {}) or {}

        return LLMResponse(
            content=content,
            model=response_metadata.get("model_name", self._model),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )
