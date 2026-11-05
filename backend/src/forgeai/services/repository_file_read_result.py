from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RepositoryFileReadResult:
    """Structured result returned when reading a repository file."""

    status: Literal["available", "unavailable"]
    file_path: str
    content: str | None = None
    sha256: str | None = None
    error: str | None = None
    truncated: bool = False
