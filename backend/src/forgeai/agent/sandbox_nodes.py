from forgeai.agent.state import ForgeAgentState
from forgeai.execution.sandbox.base import SandboxProvider


def create_sandbox_node(
    sandbox_provider: SandboxProvider,
    timeout_seconds: int,
):
    """Create and initialize an isolated sandbox."""

    def sandbox_node(state: ForgeAgentState) -> dict:
        if state.get("status") == "failed":
            return {}

        session = None

        try:
            session = sandbox_provider.create(timeout_seconds=timeout_seconds)

            return {
                "sandbox_id": session.sandbox_id,
                "sandbox_session": session,
                "status": "sandbox_created",
                "error": "",
            }

        except Exception as error:
            if session is not None:
                try:
                    sandbox_provider.terminate(session)
                except Exception:
                    pass

            return {
                "status": "failed",
                "error": f"Sandbox initialization failed: {error}",
            }

    return sandbox_node
