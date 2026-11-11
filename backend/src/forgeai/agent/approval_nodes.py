
from collections.abc import Callable

from sqlalchemy.orm import Session
from langgraph.types import interrupt

from forgeai.domain.patch_approval import ApprovalStatus
from forgeai.application.patch_approval_service import (
    PatchApprovalService,
    PatchApprovalStateError,
)
from forgeai.infrastructure.repositories.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)
from forgeai.infrastructure.repositories.patch_approval_repository import (
    SQLAlchemyPatchApprovalRepository,
)


SessionFactory = Callable[[], Session]


def create_approval_node(
    session_factory: SessionFactory,
):
    """Create and persist a pending approval for the prepared patch."""

    def approval_node(state: dict) -> dict:
        task_id = state.get("task_id")
        agent_run_id = state.get("agent_run_id")
        patch_sha256 = state.get("patch_sha256")

        if not task_id or not agent_run_id or not patch_sha256:
            return {
                "status": "failed",
                "error": "Missing task, agent run, or patch fingerprint.",
            }

        try:
            with session_factory() as session:
                approval_service = PatchApprovalService(
                    session=session,
                    approval_repository=SQLAlchemyPatchApprovalRepository(
                        session
                    ),
                    agent_run_repository=SQLAlchemyAgentRunRepository(
                        session
                    ),
                )

                approval = approval_service.create_approval(
                    task_id=task_id,
                    agent_run_id=agent_run_id,
                    patch_sha256=patch_sha256,
                )

            return {
                "approval_id": approval.approval_id,
                "status": "awaiting_approval",
            }

        except Exception as exc:
            return {
                "status": "failed",
                "error": f"Failed to create patch approval: {exc}",
            }

    return approval_node


def create_human_approval_node(
    session_factory: SessionFactory,
):
    """Pause execution and verify the persisted human decision."""

    def human_approval_node(state: dict) -> dict:
        approval_id = state.get("approval_id")
        task_id = state.get("task_id")
        agent_run_id = state.get("agent_run_id")
        patch_sha256 = state.get("patch_sha256")

        if not all((approval_id, task_id, agent_run_id, patch_sha256)):
            return {
                "status": "failed",
                "error": "Missing information required to verify approval.",
            }

        # Pause execution until an external reviewer resumes the graph.
        # The resume payload is deliberately not trusted as authorization.
        interrupt(
            {
                "approval_id": approval_id,
                "task_id": task_id,
                "agent_run_id": agent_run_id,
                "patch_sha256": patch_sha256,
                "message": "Human approval is required before patch execution.",
            }
        )

        try:
            with session_factory() as session:
                approval_service = PatchApprovalService(
                    session=session,
                    approval_repository=SQLAlchemyPatchApprovalRepository(
                        session
                    ),
                    agent_run_repository=SQLAlchemyAgentRunRepository(
                        session
                    ),
                )

                approval = approval_service.get_approval(approval_id)

                # Verify that this approval belongs to this exact run.
                if approval.task_id != task_id:
                    raise PatchApprovalStateError(
                        "Approval belongs to a different task."
                    )

                if approval.agent_run_id != agent_run_id:
                    raise PatchApprovalStateError(
                        "Approval belongs to a different agent run."
                    )

                # Verify that the approved patch is the patch in graph state.
                if approval.patch_sha256 != patch_sha256:
                    raise PatchApprovalStateError(
                        "Approval fingerprint does not match the prepared patch."
                    )

                if approval.status == ApprovalStatus.REJECTED:
                    return {
                        "human_approval_status": "rejected",
                        "status": "rejected",
                    }

                if approval.status != ApprovalStatus.APPROVED:
                    raise PatchApprovalStateError(
                        "The approval has not been approved by a reviewer."
                    )

                return {
                    "human_approval_status": "approved",
                    "status": "approval_granted",
                }

        except Exception as exc:
            return {
                "status": "failed",
                "error": f"Human approval verification failed: {exc}",
            }

    return human_approval_node
