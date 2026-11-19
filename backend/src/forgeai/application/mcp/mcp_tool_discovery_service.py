
from dataclasses import dataclass
from typing import Any

from forgeai.infrastructure.mcp import MCPClientManager


@dataclass(frozen=True, slots=True)
class DiscoveredMCPTool:
    server_name: str
    name: str
    description: str | None
    input_schema: dict[str, Any]


class MCPToolDiscoveryService:
    """Discovers and registers tools exposed by MCP servers."""

    def __init__(self, client_manager: MCPClientManager) -> None:
        self._client_manager = client_manager
        self._registry: dict[tuple[str, str], DiscoveredMCPTool] = {}

    async def discover(self, server_name: str) -> list[DiscoveredMCPTool]:
        tools = await self._client_manager.list_tools(server_name)

        discovered: list[DiscoveredMCPTool] = []
        new_registry = {
            key: value
            for key, value in self._registry.items()
            if key[0] != server_name
        }

        for tool in tools:
            input_schema = dict(tool.inputSchema)

            discovered_tool = DiscoveredMCPTool(
                server_name=server_name,
                name=tool.name,
                description=tool.description,
                input_schema=input_schema,
            )

            key = (server_name, tool.name)

            if key in new_registry:
                raise ValueError(
                    f"Duplicate MCP tool '{tool.name}' from '{server_name}'."
                )

            new_registry[key] = discovered_tool
            discovered.append(discovered_tool)

        self._registry = new_registry
        return discovered

    def get_tool(
        self,
        server_name: str,
        tool_name: str,
    ) -> DiscoveredMCPTool:
        tool = self._registry.get((server_name, tool_name))

        if tool is None:
            raise LookupError(
                f"Tool '{tool_name}' has not been discovered "
                f"from MCP server '{server_name}'."
            )

        return tool

    def get_tools(self, server_name: str) -> list[DiscoveredMCPTool]:
        return [
            tool
            for (registered_server, _), tool in self._registry.items()
            if registered_server == server_name
        ]

    def remove_server(self, server_name: str) -> None:
        self._registry = {
            key: value
            for key, value in self._registry.items()
            if key[0] != server_name
        }
