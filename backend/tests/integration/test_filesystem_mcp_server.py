
import asyncio
import sys

from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig


async def test_filesystem_mcp_server_discovers_and_executes_tools():
    manager = MCPClientManager()

    config = MCPServerConfig(
        name="filesystem",
        command=sys.executable,
        args=(
            "-m",
            "forgeai.infrastructure.mcp.servers.filesystem_server",
        ),
    )

    try:
        async with asyncio.timeout(30):
            await manager.connect(config)

        assert manager.is_connected("filesystem")

        async with asyncio.timeout(30):
            tools = await manager.list_tools("filesystem")

        tool_names = {tool.name for tool in tools}

        expected_tools = {
            "list_files",
            "read_file",
            "search_files",
            "get_file_info",
        }

        assert expected_tools.issubset(tool_names)

        async with asyncio.timeout(30):
            result = await manager.call_tool(
                "filesystem",
                "list_files",
                {
                    "directory": ".",
                    "recursive": False,
                },
            )

        assert not result.isError
        assert result.content

        print("\nDiscovered tools:", sorted(tool_names))
        print("\nWorkspace listing:", result.content)

    finally:
        await manager.disconnect_all()
