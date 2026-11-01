from forgeai.agent.state import ForgeAgentState
from forgeai.services.repository_inspector import RepositoryInspector


def prepare_task_node(state: ForgeAgentState) -> dict:
    """Validate the task input and prepare a basic task context"""

    description = state["task_description"].strip()
    repository_url = state["repository_url"].strip()
    repository_path = state.get("repository_path", "").strip()

    if not description:
        return {"status": "failed", "error": "Task description cannot be empty."}

    if not repository_url:
        return {"status": "failed", "error": "Repository URL cannot be empty."}

    if not repository_path:
        return {
            "status": "failed",
            "error": "Local repository path cannot be empty.",
        }

    return {
        "repository_context": (
            f"Target repository: {repository_url}\n" f"Engineering task: {description}"
        ),
        "status": "in_progress",
    }


def inspect_repostiory_node(state: ForgeAgentState) -> dict:
    """Inspect the local repository and update the agent state."""

    repository_path = state["repository_path"]
    inspector = RepositoryInspector()
    result = inspector.inspect(repository_path)

    if result.status == "unavailable":
        return {
            "repository_status": result.status,
            "repository_files": [],
            "repository_truncated": result.truncated,
            "status": "failed",
            "error": result.error or "Repository inspection failed.",
        }

    return {
        "repository_status": result.status,
        "repository_files": result.files,
        "repository_truncated": result.truncated,
        "status": "repository_inspected",
    }


def create_initial_plan_node(state: ForgeAgentState) -> dict:
    """Create a deterministic plan without an LLM"""

    if state.get("status") == "failed":
        return {}

    return {
        "plan": [
            "Inspect the repository structure and relevent files.",
            "Identify the likely cause of the problem.",
            "Propose the smallest appropriate code changes.",
            "Run relevent tests in an isolated environment.",
            "Review the result before requesting the approval.",
        ],
        "status": "plan_created",
    }
