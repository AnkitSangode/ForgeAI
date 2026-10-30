from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RepositoryInspectionResult:

    """Structured result returned by repository inspection."""

    status: Literal["available", "unavailable"]
    files: list[str]
    error: str | None = None