from pathlib import PurePosixPath

REPOSITORY_ROOT = "repository"


def resolve_repository_file_path(file_path: str) -> str:
    """Convert a safe repository-relative path to a workspace-relative path."""

    if not file_path or "\x00" in file_path or "\\" in file_path:
        raise ValueError("Invalid repository file path.")

    path = PurePosixPath(file_path)

    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
        or str(path) != file_path
    ):
        raise ValueError("Unsafe repository file path.")

    return str(PurePosixPath(REPOSITORY_ROOT) / path)
