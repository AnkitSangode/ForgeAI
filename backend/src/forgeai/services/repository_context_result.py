from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RepositoryFileContext:
    """Represents the contents of one repository file."""

    file_path: str
    content: str


@dataclass(frozen=True)
class RepositoryContextResult:
    """Structured result returned by repository context construction."""

    status: Literal["available", "unavailable", "partial"]
    files: list[RepositoryFileContext]
    total_bytes: int
    skipped_files: list[str]
    errors: list[str]
