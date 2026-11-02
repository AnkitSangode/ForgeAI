from typing import Any

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    content: Any
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
