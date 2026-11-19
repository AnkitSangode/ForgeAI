
from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMToolDefinition(BaseModel):
    """Provider-independent description of a callable tool."""

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any]


class LLMToolCall(BaseModel):
    """A tool invocation requested by an LLM."""

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    """Provider-independent conversation message."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    tool_name: str | None = None


class LLMToolCallResponse(BaseModel):
    """Normalized response from an LLM tool-calling request."""

    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
