from forgeai.agent.coder import CoderAgent
from forgeai.agent.coder_schema import CoderResponse
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.researcher_schema import ResearchResponse
from forgeai.agent.reviewer import ReviewerAgent
from forgeai.agent.schemas import PlanResponse
from forgeai.agent.state import ForgeAgentState
from forgeai.application.repository_clone_service import (
    RepositoryCloneService,
)
from forgeai.execution.sandbox.base import (
    SandboxProvider,
    SandboxSession,
)
from forgeai.llm.exceptions import LLMError
from forgeai.services.repository_context_builder import (
    RepositoryContextBuilder,
)
from forgeai.services.repository_inspector import (
    SandboxRepositoryInspector,
)
from forgeai.services.sandbox_repository_file_reader import (
    SandboxRepositoryFileReader,
)
from forgeai.services.session_bound_repository_file_reader import (
    SessionBoundRepositoryFileReader,
)


def get_sandbox_session(
    state: ForgeAgentState,
    sandbox_provider: SandboxProvider,
) -> SandboxSession:
    """Reconnect to an existing sandbox using its persisted ID."""

    sandbox_id = state.get("sandbox_id")

    if not sandbox_id:
        raise ValueError("Sandbox ID is missing from the agent state.")

    return sandbox_provider.connect(sandbox_id)


def prepare_task_node(state: ForgeAgentState) -> dict:
    """Validate task input before allocating sandbox resources."""

    description = state.get("task_description", "").strip()
    repository_url = state.get("repository_url", "").strip()

    if not description:
        return {
            "status": "failed",
            "error": "Task description cannot be empty.",
        }

    if not repository_url:
        return {
            "status": "failed",
            "error": "Repository URL cannot be empty.",
        }

    return {
        "task_description": description,
        "repository_url": repository_url,
        "repository_path": "repository",
        "repository_context": (
            f"Target repository: {repository_url}\nEngineering task: {description}"
        ),
        "status": "in_progress",
        "error": "",
    }


def create_repository_clone_node(
    sandbox_provider: SandboxProvider,
):
    """Clone the target GitHub repository into the active sandbox."""

    clone_service = RepositoryCloneService(
        sandbox_provider=sandbox_provider,
    )

    def clone_repository_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        try:
            session = get_sandbox_session(
                state=state,
                sandbox_provider=sandbox_provider,
            )

            result = clone_service.clone(
                session=session,
                repository_url=state["repository_url"],
            )

            return {
                "repository_name": result.repository_name,
                "repository_path": result.repository_path,
                "repository_commit_sha": result.commit_sha,
                "repository_remote_url": result.remote_url,
                "status": "repository_cloned",
                "error": "",
            }

        except Exception as error:
            return {
                "status": "failed",
                "error": f"Repository cloning failed: {error}",
            }

    return clone_repository_node


def create_repository_inspection_node(
    sandbox_provider: SandboxProvider,
):
    """Inspect repository files inside the active sandbox."""

    inspector = SandboxRepositoryInspector(
        sandbox_provider=sandbox_provider,
    )

    def inspect_repository_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        try:
            session = get_sandbox_session(
                state=state,
                sandbox_provider=sandbox_provider,
            )

            result = inspector.inspect(
                session=session,
                repository_path=state.get(
                    "repository_path",
                    "repository",
                ),
            )

            if result.status == "unavailable":
                return {
                    "repository_status": result.status,
                    "repository_files": [],
                    "repository_truncated": False,
                    "status": "failed",
                    "error": (result.error or "Repository inspection failed."),
                }

            return {
                "repository_status": result.status,
                "repository_files": result.files,
                "repository_truncated": result.truncated,
                "status": "repository_inspected",
                "error": "",
            }

        except Exception as error:
            return {
                "status": "failed",
                "error": f"Repository inspection failed: {error}",
            }

    return inspect_repository_node


def create_repository_context_node(
    sandbox_provider: SandboxProvider,
):
    """Build bounded repository context from sandbox files."""

    sandbox_reader = SandboxRepositoryFileReader(
        sandbox_provider=sandbox_provider,
    )

    def build_context_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        try:
            session = get_sandbox_session(
                state=state,
                sandbox_provider=sandbox_provider,
            )

            repository_path = state.get(
                "repository_path",
                "repository",
            )
            repository_files = state.get("repository_files", [])

            session_reader = SessionBoundRepositoryFileReader(
                sandbox_reader=sandbox_reader,
                session=session,
            )

            context_builder = RepositoryContextBuilder(
                file_reader=session_reader,
            )

            result = context_builder.build(
                repository_path=repository_path,
                file_paths=repository_files,
            )

            context_files = [
                {
                    "file_path": file.file_path,
                    "content": file.content,
                    "sha256": file.sha256,
                }
                for file in result.files
            ]

            if result.status == "unavailable":
                return {
                    "repository_context_files": context_files,
                    "repository_context_status": result.status,
                    "repository_context_bytes": result.total_bytes,
                    "repository_context_skipped_files": (result.skipped_files),
                    "repository_context_errors": result.errors,
                    "status": "failed",
                    "error": (
                        result.errors[0] if result.errors else "Unable to build repository context."
                    ),
                }

            return {
                "repository_context_files": context_files,
                "repository_context_status": result.status,
                "repository_context_bytes": result.total_bytes,
                "repository_context_skipped_files": (result.skipped_files),
                "repository_context_errors": result.errors,
                "status": "context_built",
                "error": "",
            }

        except Exception as error:
            return {
                "status": "failed",
                "error": (f"Repository context building failed: {error}"),
            }

    return build_context_node


def create_planner_node(planner_agent: PlannerAgent):
    """Create a LangGraph node using an injected PlannerAgent."""

    def planner_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        context_parts = []

        for file in state.get("repository_context_files", []):
            context_parts.append(f"FILE: {file['file_path']}\nCONTENT:\n{file['content']}")

        repository_context = "\n\n".join(context_parts)

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
                "error": "",
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
                "error": ("Researcher cannot run because no plan is available."),
            }

        repository_context_files = state.get(
            "repository_context_files",
            [],
        )

        if not repository_context_files:
            return {
                "status": "failed",
                "error": ("Researcher cannot run because repository context is unavailable."),
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
    """Create a LangGraph node for code generation and revisions."""

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

        repository_context_files = state.get(
            "repository_context_files",
            [],
        )

        if not repository_context_files:
            return {
                "status": "failed",
                "error": ("Coder cannot run because repository context is unavailable."),
            }

        try:
            plan = PlanResponse.model_validate(plan_data)
            research = ResearchResponse.model_validate(research_data)

            # Count every code generation, including the initial attempt.
            review_attempts = state.get("review_attempts", 0) + 1

            code_changes = coder_agent.generate_changes(
                task_description=state["task_description"],
                plan=plan,
                research=research,
                repository_context_files=repository_context_files,
                review_feedback=state.get("review_feedback"),
            )

            return {
                "code_changes": code_changes.model_dump(mode="json"),
                "review_attempts": review_attempts,
                "status": "code_changes_generated",
                "error": "",
            }

        except (LLMError, ValueError) as error:
            return {
                "status": "failed",
                "error": str(error),
            }

    return coder_node


def create_reviewer_node(reviewer_agent: ReviewerAgent):
    """Create a LangGraph node for reviewing generated code changes."""

    def reviewer_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        plan_data = state.get("plan")
        research_data = state.get("research")
        code_changes_data = state.get("code_changes")

        if not plan_data:
            return {
                "status": "failed",
                "error": "Reviewer cannot run because no plan is available.",
            }

        if not research_data:
            return {
                "status": "failed",
                "error": ("Reviewer cannot run because no research is available."),
            }

        if not code_changes_data:
            return {
                "status": "failed",
                "error": ("Reviewer cannot run because no code changes are available."),
            }

        repository_context_files = state.get(
            "repository_context_files",
            [],
        )

        if not repository_context_files:
            return {
                "status": "failed",
                "error": ("Reviewer cannot run because repository context is unavailable."),
            }

        try:
            plan = PlanResponse.model_validate(plan_data)
            research = ResearchResponse.model_validate(research_data)
            code_changes = CoderResponse.model_validate(code_changes_data)

            review = reviewer_agent.review(
                task_description=state["task_description"],
                plan=plan,
                research=research,
                code_changes=code_changes,
                repository_context_files=repository_context_files,
            )

            review_feedback = ""

            if review.decision == "changes_requested":
                feedback_parts = [
                    f"Review summary: {review.summary}",
                ]

                for index, finding in enumerate(review.findings, start=1):
                    feedback_parts.append(
                        f"{index}. Severity: {finding.severity}\n"
                        f"File: {finding.file_path}\n"
                        f"Issue: {finding.description}\n"
                        f"Recommendation: {finding.recommendation}"
                    )

                review_feedback = "\n\n".join(feedback_parts)

            return {
                "review": review.model_dump(mode="json"),
                "review_feedback": review_feedback,
                "status": "review_completed",
                "error": "",
            }

        except (LLMError, ValueError) as error:
            return {
                "status": "failed",
                "error": str(error),
            }

    return reviewer_node
