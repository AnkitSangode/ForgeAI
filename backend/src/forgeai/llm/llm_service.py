
import logging
from collections.abc import Sequence
from time import perf_counter
from typing import TypeVar

from pydantic import BaseModel

from forgeai.llm.base import LLMProvider
from forgeai.llm.schemas import LLMResponse
from forgeai.llm.tool_schemas import (
    LLMMessage,
    LLMToolCallResponse,
    LLMToolDefinition,
)
from forgeai.telemetry.langfuse_client import LangfuseTelemetry

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class LLMService:
    """Application service for LLM interactions with telemetry."""

    def __init__(
        self,
        provider: LLMProvider,
        telemetry: LangfuseTelemetry | None = None,
    ) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def generate(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
    ) -> LLMResponse:
        """Generate a response through the configured provider."""

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        if self._telemetry is None or not self._telemetry.enabled:
            return self._provider.generate(
                prompt=prompt,
                response_schema=response_schema,
            )

        started_at = perf_counter()

        with self._telemetry.generation(
            name="llm.generate",
            model=self._configured_model(),
            input_data={"prompt_chars": len(prompt)},
            metadata={
                "provider": self._provider.__class__.__name__,
                "structured_output": response_schema is not None,
            },
        ) as generation:
            try:
                response = self._provider.generate(
                    prompt=prompt,
                    response_schema=response_schema,
                )

                latency_ms = round(
                    (perf_counter() - started_at) * 1000,
                    2,
                )

                generation.update(
                    model=response.model,
                    output={
                        "response_chars": len(str(response.content)),
                    },
                    usage_details=self._usage_details(
                        response.input_tokens,
                        response.output_tokens,
                    ),
                    metadata={
                        "latency_ms": latency_ms,
                        "provider": self._provider.__class__.__name__,
                    },
                )

                return response

            except Exception as exc:
                generation.update(
                    level="ERROR",
                    status_message=type(exc).__name__,
                    metadata={
                        "latency_ms": round(
                            (perf_counter() - started_at) * 1000,
                            2,
                        ),
                    },
                )
                raise

    def generate_with_tools(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolDefinition],
    ) -> LLMToolCallResponse:
        """Generate a response that may request tool execution."""

        if not messages:
            raise ValueError("At least one message is required.")

        if not tools:
            raise ValueError("At least one tool definition is required.")

        if self._telemetry is None or not self._telemetry.enabled:
            return self._provider.generate_with_tools(
                messages=messages,
                tools=tools,
            )

        started_at = perf_counter()

        with self._telemetry.generation(
            name="llm.generate_with_tools",
            model=self._configured_model(),
            input_data={
                "message_count": len(messages),
                "tool_count": len(tools),
            },
            metadata={
                "provider": self._provider.__class__.__name__,
                "available_tools": [tool.name for tool in tools],
            },
        ) as generation:
            try:
                response = self._provider.generate_with_tools(
                    messages=messages,
                    tools=tools,
                )

                latency_ms = round(
                    (perf_counter() - started_at) * 1000,
                    2,
                )

                generation.update(
                    model=response.model,
                    output={
                        "response_chars": len(response.content or ""),
                        "tool_call_count": len(response.tool_calls),
                        "requested_tools": [
                            call.name for call in response.tool_calls
                        ],
                    },
                    usage_details=self._usage_details(
                        response.input_tokens,
                        response.output_tokens,
                    ),
                    metadata={
                        "latency_ms": latency_ms,
                        "provider": self._provider.__class__.__name__,
                    },
                )

                return response

            except Exception as exc:
                generation.update(
                    level="ERROR",
                    status_message=type(exc).__name__,
                    metadata={
                        "latency_ms": round(
                            (perf_counter() - started_at) * 1000,
                            2,
                        ),
                    },
                )
                raise

    def _configured_model(self) -> str:
        """Return the provider's configured model for initial tracing."""

        model = getattr(self._provider, "_model", None)
        return str(model or self._provider.__class__.__name__)

    @staticmethod
    def _usage_details(
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> dict[str, int]:
        """Include only token counts actually reported by the provider."""

        usage: dict[str, int] = {}

        if input_tokens is not None:
            usage["input"] = input_tokens

        if output_tokens is not None:
            usage["output"] = output_tokens

        return usage
