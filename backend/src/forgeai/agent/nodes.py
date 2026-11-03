from forgeai.agent.coder import CoderAgent
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.researcher_schema import ResearchResponse
from forgeai.agent.schemas import PlanResponse
from forgeai.agent.state import ForgeAgentState
from forgeai.llm.exceptions import LLMError
from forgeai.services.repository_context_builder import RepositoryContextBuilder
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
            f"Target repository: {repository_url}\nEngineering task: {description}"
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


def create_planner_node(planner_agent: PlannerAgent):
    """Create a LangGraph node using an injected PlannerAgent."""

    def planner_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        # Convert the repository's selected files into readable context.
        context_parts = []

        for file in state.get("repository_context_files", []):
            context_parts.append(f"FILE: {file['file_path']}\nCONTENT:\n{file['content']}")

        repository_context = "\n\n".join(context_parts)

        # Include metadata so the Planner knows whether context is incomplete.
        context_status = state.get(
            "repository_context_status",
            "unavailable",
        )

        repository_context = (
            f"Repository context status: {context_status}\n"
            f"Repository context bytes: "
            f"{state.get('repository_context_bytes', 0)}\n"
            f"Skipped files: "
            f"{state.get('repository_context_skipped_files', [])}\n"
            f"Context errors: "
            f"{state.get('repository_context_errors', [])}\n\n"
            f"{repository_context}"
        )

        try:
            plan = planner_agent.generate_plan(
                task_description=state["task_description"],
                repository_context=repository_context,
            )

            return {
                "plan": plan.model_dump(mode="json"),
                "status": "plan_created",
            }

        except LLMError as error:
            return {
                "status": "failed",
                "error": str(error),
            }

    return planner_node


def create_researcher_node(researcher_agent: ResearcherAgent):
    """Create a LangGraph node for repository research."""

    def researcher_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        plan_data = state.get("plan")

        if not plan_data:
            return {
                "status": "failed",
                "error": "Researcher cannot run because no plan is available.",
            }

        repository_context_files = state.get("repository_context_files", [])

        if not repository_context_files:
            return {
                "status": "failed",
                "error": "Researcher cannot run because repository context is unavailable.",
            }

        try:
            plan = PlanResponse.model_validate(plan_data)

            research = researcher_agent.research(
                task_description=state["task_description"],
                plan=plan,
                repository_context_files=repository_context_files,
            )

            return {
                "research": research.model_dump(mode="json"),
                "status": "research_completed",
                "error": "",
            }

        except (LLMError, ValueError) as error:
            return {
                "status": "failed",
                "error": str(error),
            }

    return researcher_node


def create_coder_node(coder_agent: CoderAgent):
    def coder_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        plan_data = state.get("plan")
        if not plan_data:
            return {
                "status": "failed",
                "error": "Coder cannot run because no plan is available.",
            }

        research_data = state.get("research")
        if not research_data:
            return {
                "status": "failed",
                "error": "Coder cannot run because no research is available.",
            }

        repository_context_files = state.get("repository_context_files", [])

        if not repository_context_files:
            return {
                "status": "failed",
                "error": "Coder cannot run because repository context is unavailable.",
            }

        try:
            plan = PlanResponse.model_validate(plan_data)
            research = ResearchResponse.model_validate(research_data)

            code_changes = coder_agent.generate_changes(
                task_description=state["task_description"],
                plan=plan,
                research=research,
                repository_context_files=repository_context_files,
            )

            return {
                "code_changes": code_changes.model_dump(mode="json"),
                "status": "code_changes_generated",
                "error": "",
            }

        except (LLMError, ValueError) as error:
            return {
                "status": "failed",
                "error": str(error),
            }

    return coder_node


def build_repository_context_node(state: ForgeAgentState) -> dict:
    """Build bounded repository context from discovered files."""

    repository_path = state["repository_path"]
    repository_files = state.get("repository_files", [])

    context_builder = RepositoryContextBuilder()

    result = context_builder.build(
        repository_path=repository_path,
        file_paths=repository_files,
    )

    context_files = [
        {
            "file_path": file.file_path,
            "content": file.content,
        }
        for file in result.files
    ]

    if result.status == "unavailable":
        return {
            "repository_context_files": context_files,
            "repository_context_status": result.status,
            "repository_context_bytes": result.total_bytes,
            "repository_context_skipped_files": result.skipped_files,
            "repository_context_errors": result.errors,
            "status": "failed",
            "error": (result.errors[0] if result.errors else "Unable to build repository context."),
        }

    return {
        "repository_context_files": context_files,
        "repository_context_status": result.status,
        "repository_context_bytes": result.total_bytes,
        "repository_context_skipped_files": result.skipped_files,
        "repository_context_errors": result.errors,
        "status": "context_built",
    }
