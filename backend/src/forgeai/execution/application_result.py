from dataclasses import dataclass


@dataclass(frozen=True)
class PatchApplicationResult:
    """Represents the outcome of applying a patch in the sandbox."""

    success: bool
    changed_files: list[str]
    message: str
