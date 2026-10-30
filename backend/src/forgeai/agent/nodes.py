from forgeai.agent.state import ForgeAgentState


def prepare_task_node(state: ForgeAgentState) -> dict:
    """Validate the task input and prepare a basic task context"""

    description = state["task_description"].strip()
    repository_url = state["repository_url"].strip()

    if not description:
        return {"status": "failed", "error": "Task description cannot be empty."}

    if not repository_url:
        return {"status": "failed", "error": "Repository URL cannot be empty."}

    return {
        "repository_context": (
            f"Target repository: {repository_url}\n" f"Engineering task: {description}"
        ),
        "status": "in_progress",
    }


def create_initial_plan_node(state: ForgeAgentState) -> dict:
    """Create a deterministic plan without an LLM"""

    if state.get("status") == "failed":
        return {}

    return {
        "Plan": [
            "Inspect the repository structure and relevent files.",
            "Identify the likely cause of the problem.",
            "Propose the smallest appropriate code changes.",
            "Run relevent tests in an isolated environment.",
            "Review the result before requesting the approval.",
        ],
        "status": "plan_created",
    }
