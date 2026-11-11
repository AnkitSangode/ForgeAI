from typing import Any, NotRequired, TypedDict


class ForgeAgentState(TypedDict):
    """Serializable data passed between nodes during one agent run."""

    # Task information
    task_id: str
    task_description: str
    repository_url: str

    # Repository context
    repository_context_files: NotRequired[list[dict[str, str]]]
    repository_context_status: NotRequired[str]
    repository_context_bytes: NotRequired[int]
    repository_context_skipped_files: NotRequired[list[str]]
    repository_context_errors: NotRequired[list[str]]

    # Repository inspection
    repository_path: NotRequired[str]
    repository_context: NotRequired[str]
    repository_status: NotRequired[str]
    repository_files: NotRequired[list[str]]
    repository_truncated: NotRequired[bool]

    # Repository metadata
    repository_name: NotRequired[str]
    repository_remote_url: NotRequired[str]
    repository_commit_sha: NotRequired[str]

    # Sandbox information
    sandbox_id: NotRequired[str]

    # Planner output
    plan: NotRequired[dict[str, Any]]

    # Researcher output
    research: NotRequired[dict[str, Any]]

    # Coder output
    code_changes: NotRequired[dict[str, Any]]

    # Reviewer output
    review: NotRequired[dict[str, Any]]
    review_feedback: NotRequired[str]
    review_attempts: NotRequired[int]

    # Workflow status
    status: NotRequired[str]
    error: NotRequired[str]
