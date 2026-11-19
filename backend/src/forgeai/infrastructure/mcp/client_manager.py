
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from forgeai.infrastructure.mcp.server_config import MCPServerConfig


@dataclass(slots=True)
class _MCPConnection:
    """Resources belonging to one active MCP server connection."""

    stack: AsyncExitStack
    session: ClientSession


class MCPClientManager:
    """Manages trusted MCP server connections over stdio."""

    def __init__(self) -> None:
        self._connections: dict[str, _MCPConnection] = {}

    async def connect(self, config: MCPServerConfig) -> None:
        """Start an MCP server and initialize its client session."""

        if config.name in self._connections:
            raise ValueError(
                f"MCP server '{config.name}' is already connected."
            )

        stack = AsyncExitStack()

        try:
            server_parameters = StdioServerParameters(
                command=config.command,
                args=list(config.args),
                env=dict(config.env) or None,
            )

            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(server_parameters)
            )

            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await session.initialize()

            self._connections[config.name] = _MCPConnection(
                stack=stack,
                session=session,
            )

        except Exception:
            await stack.aclose()
            raise

    async def list_tools(self, server_name: str) -> list[Any]:
        """Discover tools exposed by a connected MCP server."""

        connection = self._get_connection(server_name)

        result = await connection.session.list_tools()

        return list(result.tools)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Invoke a tool exposed by a connected MCP server."""

        if not tool_name.strip():
            raise ValueError("Tool name cannot be empty.")

        connection = self._get_connection(server_name)

        return await connection.session.call_tool(
            tool_name,
            arguments=arguments,
        )

    async def disconnect(self, server_name: str) -> None:
        """Close one MCP server connection."""

        connection = self._connections.pop(server_name, None)

        if connection is None:
            return

        await connection.stack.aclose()

    async def disconnect_all(self) -> None:
        """Close every active MCP server connection."""

        connections = list(self._connections.values())
        self._connections.clear()

        errors: list[BaseException] = []

        for connection in connections:
            try:
                await connection.stack.aclose()
            except (OSError, RuntimeError, ValueError) as exc:
                errors.append(exc)

        if errors:
            raise ExceptionGroup(
                "One or more MCP connections failed to close.",
                errors,
            )

    def is_connected(self, server_name: str) -> bool:
        return server_name in self._connections

    def _get_connection(self, server_name: str) -> _MCPConnection:
        connection = self._connections.get(server_name)

        if connection is None:
            raise ConnectionError(
                f"MCP server '{server_name}' is not connected."
            )

        return connection
