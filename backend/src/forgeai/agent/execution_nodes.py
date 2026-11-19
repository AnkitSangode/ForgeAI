from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from forgeai.application.patch_approval_service import PatchApprovalService
from forgeai.application.patch_execution_service import PatchExecutionService
from forgeai.infrastructure.repositories.agent_run_repository import SQLAlchemyAgentRunRepository
from forgeai.infrastructure.repositories.patch_approval_repository import (
    SQLAlchemyPatchApprovalRepository,
)
from forgeai.infrastructure.repositories.patch_execution_repository import (
    SQLAlchemyPatchExecutionRepository,
)

SessionFactory = Callable[[], Session]


def create_execution_record_node(session_factory: SessionFactory):
    """Create a durable execution record after persisted approval is verified."""

    def create_execution_node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        approval_id = state.get("approval_id")
        task_id = state.get("task_id")
        agent_run_id = state.get("agent_run_id")
        patch_sha256 = state.get("patch_sha256")
        human_status = state.get("human_approval_status")

        if human_status != "approved":
            return {
                "status": "failed",
                "error": "Execution cannot be created without verified human approval.",
            }

        if not all((approval_id, task_id, agent_run_id, patch_sha256)):
            return {
                "status": "failed",
                "error": "Missing approval, task, run, or patch fingerprint.",
            }

        try:
            with session_factory() as session:
                approval_repository = SQLAlchemyPatchApprovalRepository(session)
                run_repository = SQLAlchemyAgentRunRepository(session)
                execution_repository = SQLAlchemyPatchExecutionRepository(session)
                approval_service = PatchApprovalService(
                    session=session,
                    approval_repository=approval_repository,
                    agent_run_repository=run_repository,
                )
                execution_service = PatchExecutionService(
                    session=session,
                    execution_repository=execution_repository,
                    approval_service=approval_service,
                    agent_run_repository=run_repository,
                )
                execution = execution_service.create_execution(
                    approval_id=approval_id,
                    task_id=task_id,
                    agent_run_id=agent_run_id,
                    patch_sha256=patch_sha256,
                )

            return {
                "execution_id": execution.execution_id,
                "execution_status": execution.status.value,
                "status": "execution_pending",
                "error": "",
            }
        except Exception as exc:
            return {
                "status": "failed",
                "error": f"Failed to create patch execution: {exc}",
            }

    return create_execution_node


def create_approved_patch_execution_node(
    session_factory: SessionFactory,
    worker_factory: Callable[[PatchExecutionService], Any],
):
    """Create a worker per graph invocation with a short-lived DB session.

    The worker and PatchExecutionService share one SQLAlchemy session for the
    duration of the execution. The worker's lifecycle methods commit durable
    transitions; the session is closed when this node returns.
    """

    def execute_patch_node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        required = (
            state.get("execution_id"),
            state.get("sandbox_id"),
            state.get("patch_sha256"),
            state.get("code_changes"),
            state.get("repository_context_files"),
        )
        if not all(required):
            return {
                "status": "failed",
                "error": "Missing execution or prepared patch data required for execution.",
            }

        if state.get("human_approval_status") != "approved":
            return {
                "status": "failed",
                "error": "Patch execution requires verified human approval.",
            }

        try:
            from forgeai.agent.coder_schema import CoderResponse
            from forgeai.services.repository_context_result import (
                RepositoryContextResult,
                RepositoryFileContext,
            )

            coder_response = CoderResponse.model_validate(state["code_changes"])
            context_files = [
                RepositoryFileContext(
                    file_path=item["file_path"],
                    content=item["content"],
                    sha256=item["sha256"],
                )
                for item in state["repository_context_files"]
            ]
            context = RepositoryContextResult(
                status=state.get("repository_context_status", "unavailable"),
                files=context_files,
                total_bytes=state.get("repository_context_bytes", 0),
                skipped_files=state.get("repository_context_skipped_files", []),
                errors=state.get("repository_context_errors", []),
            )
            context_data = {
                "status": context.status,
                "files": [
                    {
                        "file_path": file.file_path,
                        "content": file.content,
                        "sha256": file.sha256,
                    }
                    for file in context.files
                ],
                "total_bytes": context.total_bytes,
                "skipped_files": context.skipped_files,
                "errors": context.errors,
            }

            with session_factory() as session:
                approval_repository = SQLAlchemyPatchApprovalRepository(session)
                run_repository = SQLAlchemyAgentRunRepository(session)
                execution_repository = SQLAlchemyPatchExecutionRepository(session)
                approval_service = PatchApprovalService(
                    session=session,
                    approval_repository=approval_repository,
                    agent_run_repository=run_repository,
                )
                execution_service = PatchExecutionService(
                    session=session,
                    execution_repository=execution_repository,
                    approval_service=approval_service,
                    agent_run_repository=run_repository,
                )
                worker = worker_factory(execution_service)
                result = worker.execute(
                    execution_id=state["execution_id"],
                    sandbox_id=state["sandbox_id"],
                    changes=coder_response.changes,
                    allowed_paths=set(state.get("allowed_paths", [])),
                    repository_context_data=context_data,
                    expected_patch_sha256=state["patch_sha256"],
                    tests_to_run=state.get("tests_to_run", []),
                )

            return {
                "execution_status": "succeeded" if result.success else "failed",
                "execution_result": {
                    "success": result.success,
                    "changed_files": result.changed_files,
                    "tests": [
                        {
                            "command": test.command,
                            "exit_code": test.exit_code,
                            "stdout": test.stdout,
                            "stderr": test.stderr,
                            "timed_out": test.timed_out,
                        }
                        for test in result.tests
                    ],
                    "tests_skipped": result.tests_skipped,
                    "message": result.message,
                },
                "status": "succeeded" if result.success else "failed",
                "error": "" if result.success else result.message,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "error": f"Approved patch execution failed: {exc}",
            }

    return execute_patch_node
