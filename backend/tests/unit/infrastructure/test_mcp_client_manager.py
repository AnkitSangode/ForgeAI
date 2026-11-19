
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from forgeai.infrastructure.mcp.client_manager import MCPClientManager
from forgeai.infrastructure.mcp.server_config import MCPServerConfig


class FakeAsyncContextManager:
    def __init__(self, value):
        self.value = value
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        self.exited = True
        return False


class FakeMCPSession:
    def __init__(self):
        self.initialize = AsyncMock()
        self.list_tools = AsyncMock(
            return_value=SimpleNamespace(tools=["add_numbers"])
        )
        self.call_tool = AsyncMock(
            return_value=SimpleNamespace(content=["30"], isError=False)
        )


def make_config() -> MCPServerConfig:
    return MCPServerConfig(
        name="test-server",
        command="python",
        args=("-m", "test_server"),
        env={"TEST_ENV": "true"},
    )


def test_connect_initializes_mcp_session():
    async def scenario():
        manager = MCPClientManager()
        session = FakeMCPSession()
        transport = FakeAsyncContextManager(("read", "write"))
        session_context = FakeAsyncContextManager(session)

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=transport,
            ) as stdio_mock,
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=session_context,
            ),
        ):
            await manager.connect(make_config())

        assert manager.is_connected("test-server")
        session.initialize.assert_awaited_once()

        parameters = stdio_mock.call_args.args[0]
        assert parameters.command == "python"
        assert parameters.args == ["-m", "test_server"]
        assert parameters.env == {"TEST_ENV": "true"}

    asyncio.run(scenario())


def test_connect_rejects_duplicate_server_name():
    async def scenario():
        manager = MCPClientManager()
        session = FakeMCPSession()

        transport = FakeAsyncContextManager(("read", "write"))
        session_context = FakeAsyncContextManager(session)

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=transport,
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=session_context,
            ),
        ):
            await manager.connect(make_config())

            with pytest.raises(ValueError, match="already connected"):
                await manager.connect(make_config())

        assert manager.is_connected("test-server")

    asyncio.run(scenario())


def test_list_tools_returns_discovered_tools():
    async def scenario():
        manager = MCPClientManager()
        session = FakeMCPSession()

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=FakeAsyncContextManager(("read", "write")),
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=FakeAsyncContextManager(session),
            ),
        ):
            await manager.connect(make_config())

            tools = await manager.list_tools("test-server")

        assert tools == ["add_numbers"]
        session.list_tools.assert_awaited_once()

    asyncio.run(scenario())


def test_call_tool_invokes_server_tool():
    async def scenario():
        manager = MCPClientManager()
        session = FakeMCPSession()

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=FakeAsyncContextManager(("read", "write")),
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=FakeAsyncContextManager(session),
            ),
        ):
            await manager.connect(make_config())

            result = await manager.call_tool(
                server_name="test-server",
                tool_name="add_numbers",
                arguments={"a": 10, "b": 20},
            )

        assert result.content == ["30"]
        session.call_tool.assert_awaited_once_with(
            "add_numbers",
            arguments={"a": 10, "b": 20},
        )

    asyncio.run(scenario())


def test_call_tool_rejects_empty_tool_name():
    async def scenario():
        manager = MCPClientManager()

        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            await manager.call_tool(
                server_name="test-server",
                tool_name="",
                arguments={},
            )

    asyncio.run(scenario())


def test_operations_reject_unknown_server():
    async def scenario():
        manager = MCPClientManager()

        with pytest.raises(ConnectionError, match="not connected"):
            await manager.list_tools("unknown-server")

        with pytest.raises(ConnectionError, match="not connected"):
            await manager.call_tool(
                server_name="unknown-server",
                tool_name="add_numbers",
                arguments={"a": 1, "b": 2},
            )

    asyncio.run(scenario())


def test_disconnect_closes_connection():
    async def scenario():
        manager = MCPClientManager()
        session = FakeMCPSession()

        transport = FakeAsyncContextManager(("read", "write"))
        session_context = FakeAsyncContextManager(session)

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=transport,
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=session_context,
            ),
        ):
            await manager.connect(make_config())
            await manager.disconnect("test-server")

        assert not manager.is_connected("test-server")
        assert session_context.exited
        assert transport.exited

    asyncio.run(scenario())


def test_disconnect_unknown_server_is_safe():
    async def scenario():
        manager = MCPClientManager()

        await manager.disconnect("unknown-server")

        assert not manager.is_connected("unknown-server")

    asyncio.run(scenario())


def test_disconnect_all_closes_every_connection():
    async def scenario():
        manager = MCPClientManager()

        first_session = FakeMCPSession()
        second_session = FakeMCPSession()

        first_transport = FakeAsyncContextManager(("read1", "write1"))
        second_transport = FakeAsyncContextManager(("read2", "write2"))

        first_context = FakeAsyncContextManager(first_session)
        second_context = FakeAsyncContextManager(second_session)

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                side_effect=[first_transport, second_transport],
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                side_effect=[first_context, second_context],
            ),
        ):
            await manager.connect(
                MCPServerConfig(name="server-one", command="python")
            )
            await manager.connect(
                MCPServerConfig(name="server-two", command="python")
            )

            await manager.disconnect_all()

        assert not manager.is_connected("server-one")
        assert not manager.is_connected("server-two")
        assert first_context.exited
        assert second_context.exited
        assert first_transport.exited
        assert second_transport.exited

    asyncio.run(scenario())


def test_connect_failure_cleans_up_transport():
    async def scenario():
        manager = MCPClientManager()

        transport = FakeAsyncContextManager(("read", "write"))
        session = FakeMCPSession()
        session.initialize.side_effect = RuntimeError("Initialization failed")
        session_context = FakeAsyncContextManager(session)

        with (
            patch(
                "forgeai.infrastructure.mcp.client_manager.stdio_client",
                return_value=transport,
            ),
            patch(
                "forgeai.infrastructure.mcp.client_manager.ClientSession",
                return_value=session_context,
            ),pytest.raises(RuntimeError, match="Initialization failed")
        ):
            await manager.connect(make_config())

        assert session_context.exited
        assert transport.exited
        assert not manager.is_connected("test-server")

    asyncio.run(scenario())
