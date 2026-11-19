
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ForgeAI Filesystem MCP Server")

# Load the backend .env when this server runs independently.
BACKEND_ROOT = Path(__file__).resolve().parents[5]
load_dotenv(BACKEND_ROOT / ".env")

WORKSPACE_ROOT_VALUE = os.getenv(
    "MCP_FILESYSTEM_ROOT",
    r"D:\Internship projects\forgeai",
)

WORKSPACE_ROOT = Path(WORKSPACE_ROOT_VALUE).expanduser().resolve()

if not WORKSPACE_ROOT.exists() or not WORKSPACE_ROOT.is_dir():
    raise RuntimeError(
        f"Filesystem MCP workspace does not exist: {WORKSPACE_ROOT}"
    )

MAX_FILE_SIZE = 256 * 1024
MAX_SEARCH_RESULTS = 100
MAX_LIST_RESULTS = 500

EXCLUDED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
}

SENSITIVE_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


def _resolve_workspace_path(relative_path: str) -> Path:
    """Resolve a path and ensure it remains inside the workspace."""

    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("A non-empty relative path is required.")

    requested = Path(relative_path)

    if requested.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    if ".." in requested.parts:
        raise ValueError("Path traversal is not allowed.")

    resolved = (WORKSPACE_ROOT / requested).resolve()

    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError(
            "Access outside the configured workspace is not allowed."
        ) from exc

    return resolved


def _is_sensitive(path: Path) -> bool:
    """Identify files that must not be exposed."""

    if path.name.lower() in SENSITIVE_NAMES:
        return True

    if path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True

    return False


def _is_excluded(path: Path) -> bool:
    """Check whether a path belongs to an excluded directory."""

    try:
        relative = path.relative_to(WORKSPACE_ROOT)
    except ValueError:
        return True

    return any(
        part.lower() in EXCLUDED_NAMES
        for part in relative.parts
    )


def _validate_readable_file(relative_path: str) -> Path:
    """Validate a file before reading its contents."""

    path = _resolve_workspace_path(relative_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    if not path.is_file():
        raise ValueError("The requested path is not a file.")

    if _is_excluded(path):
        raise PermissionError("Access to this directory is restricted.")

    if _is_sensitive(path):
        raise PermissionError("Access to sensitive files is restricted.")

    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(
            f"File exceeds the {MAX_FILE_SIZE}-byte read limit."
        )

    return path


@mcp.tool()
def list_files(
    directory: str = ".",
    recursive: bool = False,
) -> str:
    """List files and directories inside the configured workspace.

    Hidden and excluded directories are not exposed.
    """

    path = _resolve_workspace_path(directory)

    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not path.is_dir():
        raise ValueError("The requested path is not a directory.")

    if _is_excluded(path):
        raise PermissionError("Access to this directory is restricted.")

    entries: list[dict[str, str]] = []

    iterator = path.rglob("*") if recursive else path.iterdir()

    for item in iterator:
        if _is_excluded(item):
            continue

        # Resolve every entry to prevent symlink escapes.
        try:
            resolved = item.resolve()
            resolved.relative_to(WORKSPACE_ROOT)
        except (ValueError, OSError, RuntimeError):
            continue

        if _is_sensitive(item):
            continue

        if item.is_file() or item.is_dir():
            entries.append(
                {
                    "path": str(item.relative_to(WORKSPACE_ROOT)),
                    "type": "directory" if item.is_dir() else "file",
                }
            )

        if len(entries) >= MAX_LIST_RESULTS:
            break

    entries.sort(key=lambda item: item["path"].lower())

    return str(
        {
            "workspace": str(WORKSPACE_ROOT),
            "directory": str(path.relative_to(WORKSPACE_ROOT)),
            "recursive": recursive,
            "returned_entries": len(entries),
            "entries": entries,
        }
    )


@mcp.tool()
def read_file(file_path: str) -> str:
    """Read a UTF-8 text file inside the configured workspace."""

    path = _validate_readable_file(file_path)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "The requested file is not valid UTF-8 text."
        ) from exc

    return content


@mcp.tool()
def search_files(
    query: str,
    directory: str = ".",
    file_extension: str = "",
) -> str:
    """Search text files for a case-insensitive string.

    Searches only within the configured workspace and skips
    excluded directories, sensitive files, and oversized files.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if len(query) > 500:
        raise ValueError("Search query is too long.")

    root = _resolve_workspace_path(directory)

    if not root.exists() or not root.is_dir():
        raise ValueError("Search directory does not exist.")

    if _is_excluded(root):
        raise PermissionError("Access to this directory is restricted.")

    if file_extension and not file_extension.startswith("."):
        file_extension = "." + file_extension

    results: list[dict[str, object]] = []
    normalized_query = query.casefold()

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if _is_excluded(path) or _is_sensitive(path):
            continue

        if file_extension and path.suffix.lower() != file_extension.lower():
            continue

        try:
            resolved = path.resolve()
            resolved.relative_to(WORKSPACE_ROOT)

            if resolved.stat().st_size > MAX_FILE_SIZE:
                continue

            content = resolved.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except (OSError, ValueError, RuntimeError):
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            if normalized_query in line.casefold():
                results.append(
                    {
                        "file": str(path.relative_to(WORKSPACE_ROOT)),
                        "line": line_number,
                        "content": line.strip()[:500],
                    }
                )

                if len(results) >= MAX_SEARCH_RESULTS:
                    return str(
                        {
                            "query": query,
                            "returned_results": len(results),
                            "truncated": True,
                            "results": results,
                        }
                    )

    return str(
        {
            "query": query,
            "returned_results": len(results),
            "truncated": False,
            "results": results,
        }
    )


@mcp.tool()
def get_file_info(file_path: str) -> str:
    """Get basic metadata for a file inside the workspace."""

    path = _resolve_workspace_path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {file_path}")

    if _is_excluded(path) or _is_sensitive(path):
        raise PermissionError("Access to this path is restricted.")

    return str(
        {
            "path": str(path.relative_to(WORKSPACE_ROOT)),
            "type": "directory" if path.is_dir() else "file",
            "size_bytes": path.stat().st_size if path.is_file() else None,
            "suffix": path.suffix if path.is_file() else None,
        }
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
