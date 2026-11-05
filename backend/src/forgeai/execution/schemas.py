from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class FileSnapshot(BaseModel):
    """Trusted record of a repository file at a specific point in time."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class GitRepositoryState:
    """Snapshot of repository changes at a point in time."""

    modified_files: frozenset[str]
    untracked_files: frozenset[str]
    deleted_files: frozenset[str]
    file_hashes: tuple[tuple[str, str], ...]
