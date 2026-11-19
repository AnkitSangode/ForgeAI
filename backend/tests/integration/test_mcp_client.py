
import asyncio
import sys
from pathlib import Path

from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig

SERVER_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "mcp"
    / "addition_server.py"
)


def test_real_mcp_server_connection_discovery_and_invocation():
    async def scenario():
        manager = MCPClientManager()

        config = MCPServerConfig(
            name="addition-server",
            command=sys.executable,
            args=(str(SERVER_PATH),),
        )

        try:
            # asyncio.timeout does not create a separate task.
            async with asyncio.timeout(15):
                await manager.connect(config)

            assert manager.is_connected("addition-server")

            async with asyncio.timeout(10):
                tools = await manager.list_tools("addition-server")

            tool_names = [tool.name for tool in tools]
            assert "add_numbers" in tool_names

            async with asyncio.timeout(10):
                result = await manager.call_tool(
                    server_name="addition-server",
                    tool_name="add_numbers",
                    arguments={"a": 10, "b": 20},
                )

            assert result.isError is False
            assert len(result.content) == 1
            assert result.content[0].text == "30"

        finally:
            await manager.disconnect_all()

        assert not manager.is_connected("addition-server")

    asyncio.run(scenario())
