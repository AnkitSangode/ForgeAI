
import pytest

from forgeai.application.mcp.mcp_tool_policy import (
    MCPAuthorizationError,
    MCPToolPolicy,
)


@pytest.fixture
def policy():
    return MCPToolPolicy(
        allowed_servers=frozenset({"addition-server"}),
        allowed_tools={
            "addition-server": frozenset({"add_numbers"}),
        },
    )


def test_authorize_trusted_server(policy):
    policy.authorize_server("addition-server")


def test_reject_untrusted_server(policy):
    with pytest.raises(MCPAuthorizationError, match="not trusted"):
        policy.authorize_server("unknown-server")


def test_authorize_allowed_tool(policy):
    policy.authorize_tool("addition-server", "add_numbers")


def test_reject_unapproved_tool(policy):
    with pytest.raises(MCPAuthorizationError, match="not authorized"):
        policy.authorize_tool("addition-server", "delete_database")


def test_reject_tool_on_untrusted_server(policy):
    with pytest.raises(MCPAuthorizationError, match="not trusted"):
        policy.authorize_tool("unknown-server", "add_numbers")


def test_reject_policy_for_untrusted_server():
    with pytest.raises(ValueError, match="untrusted MCP servers"):
        MCPToolPolicy(
            allowed_servers=frozenset({"addition-server"}),
            allowed_tools={
                "unknown-server": frozenset({"dangerous_tool"}),
            },
        )


def test_reject_empty_server_allowlist():
    with pytest.raises(ValueError, match="At least one trusted"):
        MCPToolPolicy(
            allowed_servers=frozenset(),
            allowed_tools={},
        )
