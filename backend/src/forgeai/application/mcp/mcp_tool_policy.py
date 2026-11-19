
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


class MCPAuthorizationError(PermissionError):
    """Raised when an MCP server or tool is not authorized."""


@dataclass(frozen=True, slots=True)
class MCPToolPolicy:
    """Defines the MCP servers and tools ForgeAI is allowed to use."""

    allowed_servers: frozenset[str]
    allowed_tools: Mapping[str, frozenset[str]]

    def __post_init__(self) -> None:
        servers = frozenset(self.allowed_servers)

        if not servers:
            raise ValueError("At least one trusted MCP server is required.")

        if any(not name.strip() for name in servers):
            raise ValueError("Server names cannot be empty.")

        normalized_tools = {
            server: frozenset(tools)
            for server, tools in self.allowed_tools.items()
        }

        if not servers.issuperset(normalized_tools):
            raise ValueError(
                "Tool policies cannot reference untrusted MCP servers."
            )

        for server_name, tools in normalized_tools.items():
            if not server_name.strip():
                raise ValueError("Server names cannot be empty.")

            if any(not tool.strip() for tool in tools):
                raise ValueError("Tool names cannot be empty.")

        object.__setattr__(self, "allowed_servers", servers)
        object.__setattr__(
            self,
            "allowed_tools",
            MappingProxyType(normalized_tools),
        )

    def authorize_server(self, server_name: str) -> None:
        if server_name not in self.allowed_servers:
            raise MCPAuthorizationError(
                f"MCP server '{server_name}' is not trusted."
            )

    def authorize_tool(
        self,
        server_name: str,
        tool_name: str,
    ) -> None:
        self.authorize_server(server_name)

        allowed = self.allowed_tools.get(server_name, frozenset())

        if tool_name not in allowed:
            raise MCPAuthorizationError(
                f"Tool '{tool_name}' is not authorized "
                f"on MCP server '{server_name}'."
            )
