from typing import NotRequired, TypedDict


class ForgeAgentState(TypedDict):
    """Data passed between nodes during one agent run."""

    task_id: str
    task_description: str
    repository_url: str

    repository_context: NotRequired[str]
    repository_status: NotRequired[str]
    repository_files: NotRequired[list[str]]
    plan: NotRequired[list[str]]
    status: NotRequired[str]
    error: NotRequired[str] 