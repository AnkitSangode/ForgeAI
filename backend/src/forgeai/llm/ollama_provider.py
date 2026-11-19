
from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

import httpx
from ollama import Client, ResponseError
from pydantic import BaseModel, ValidationError

from forgeai.core.config import Settings
from forgeai.llm.base import LLMProvider
from forgeai.llm.exceptions import (
    LLMConnectionError,
    LLMProviderError,
    LLMResponseError,
    LLMTimeoutError,
)
from forgeai.llm.schemas import LLMResponse
from forgeai.llm.tool_schemas import (
    LLMMessage,
    LLMToolCall,
    LLMToolCallResponse,
    LLMToolDefinition,
)

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(LLMProvider):
    """LLM provider implementation using a locally running Ollama server."""

    def __init__(self, settings: Settings) -> None:
        self._model = settings.ollama_model
        self._client = Client(
            host=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
        )
        self._temperature = settings.ollama_temperature

    def generate(
        self,
        prompt: str,
        response_schema: type[T] | None = None,
    ) -> LLMResponse:
        """Generate a standard text or structured response."""

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        kwargs: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": self._temperature},
        }

        if response_schema is not None:
            kwargs["format"] = response_schema.model_json_schema()

        try:
            response = self._client.chat(**kwargs)

            content = response.message.content

            if not isinstance(content, str) or not content.strip():
                raise LLMResponseError(
                    "Ollama returned an empty response."
                )

            if response_schema is not None:
                try:
                    response_schema.model_validate_json(content)
                except ValidationError as exc:
                    raise LLMResponseError(
                        "Ollama returned invalid structured output."
                    ) from exc

            return LLMResponse(
                content=content,
                model=response.model or self._model,
                input_tokens=response.prompt_eval_count,
                output_tokens=response.eval_count,
            )

        except LLMResponseError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                "Ollama request timed out."
            ) from exc
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise LLMConnectionError(
                "Could not connect to the Ollama server."
            ) from exc
        except ResponseError as exc:
            raise LLMProviderError(
                f"Ollama provider error: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Ollama HTTP error: {exc}"
            ) from exc

    def generate_with_tools(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolDefinition],
    ) -> LLMToolCallResponse:
        """Generate a response that may contain native tool calls."""

        if not messages:
            raise ValueError("At least one message is required.")

        if not tools:
            raise ValueError("At least one tool definition is required.")

        ollama_messages: list[dict] = []

        for message in messages:
            message_data: dict = {
                "role": message.role,
                "content": message.content,
            }

            if message.role == "tool":
                if not message.tool_name:
                    raise ValueError(
                        "Tool messages must include tool_name."
                    )

                message_data["tool_name"] = message.tool_name

            if message.tool_calls:
                message_data["tool_calls"] = [
                    {
                        "function": {
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        }
                    }
                    for tool_call in message.tool_calls
                ]

            ollama_messages.append(message_data)

        ollama_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

        try:
            response = self._client.chat(
                model=self._model,
                messages=ollama_messages,
                tools=ollama_tools,
                options={"temperature": self._temperature},
            )

            content = response.message.content or ""

            parsed_tool_calls: list[LLMToolCall] = []

            for tool_call in response.message.tool_calls or []:
                function = tool_call.function
                arguments = function.arguments

                if not isinstance(arguments, dict):
                    raise LLMResponseError(
                        f"Ollama returned invalid arguments for tool "
                        f"'{function.name}'."
                    )

                parsed_tool_calls.append(
                    LLMToolCall(
                        name=function.name,
                        arguments=arguments,
                    )
                )

            if not content.strip() and not parsed_tool_calls:
                raise LLMResponseError(
                    "Ollama returned neither content nor tool calls."
                )

            return LLMToolCallResponse(
                content=content or None,
                tool_calls=parsed_tool_calls,
                model=response.model or self._model,
                input_tokens=response.prompt_eval_count,
                output_tokens=response.eval_count,
            )

        except LLMResponseError:
            raise
        except ValidationError as exc:
            raise LLMResponseError(
                "Ollama returned an invalid tool-call response."
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                "Ollama tool-calling request timed out."
            ) from exc
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise LLMConnectionError(
                "Could not connect to the Ollama server."
            ) from exc
        except ResponseError as exc:
            raise LLMProviderError(
                f"Ollama tool-calling error: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Ollama HTTP error during tool calling: {exc}"
            ) from exc
