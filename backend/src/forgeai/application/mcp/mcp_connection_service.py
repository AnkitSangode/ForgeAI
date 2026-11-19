
from forgeai.application.mcp.mcp_tool_policy import MCPToolPolicy
from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig


class MCPConnectionService:
    """Application-level MCP connection management with authorization."""

    def __init__(
        self,
        client_manager: MCPClientManager,
        policy: MCPToolPolicy,
    ) -> None:
        self._client_manager = client_manager
        self._policy = policy

    async def connect(self, config: MCPServerConfig) -> None:
        self._policy.authorize_server(config.name)
        await self._client_manager.connect(config)

    async def disconnect(self, server_name: str) -> None:
        self._policy.authorize_server(server_name)
        await self._client_manager.disconnect(server_name)

    async def disconnect_all(self) -> None:
        await self._client_manager.disconnect_all()

    def is_connected(self, server_name: str) -> bool:
        self._policy.authorize_server(server_name)
        return self._client_manager.is_connected(server_name)
