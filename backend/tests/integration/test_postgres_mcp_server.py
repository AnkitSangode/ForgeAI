
import asyncio
import json
import sys

from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig


async def test_postgres_mcp_server_discovers_and_executes_tools():
    """Verify PostgreSQL MCP startup, discovery, and real database access."""

    manager = MCPClientManager()

    config = MCPServerConfig(
        name="postgres",
        command=sys.executable,
        args=(
            "-m",
            "forgeai.infrastructure.mcp.servers.postgres_server",
        ),
    )

    try:
        # 1. Launch the independent MCP server process.
        async with asyncio.timeout(30):
            await manager.connect(config)

        assert manager.is_connected("postgres")

        # 2. Discover the tools exposed by the server.
        async with asyncio.timeout(30):
            tools = await manager.list_tools("postgres")

        tool_names = {tool.name for tool in tools}

        assert {
            "list_tables",
            "describe_table",
            "read_records",
        }.issubset(tool_names)

        # 3. Execute list_tables against the real PostgreSQL database.
        async with asyncio.timeout(30):
            result = await manager.call_tool(
                "postgres",
                "list_tables",
                {},
            )

        assert not result.isError
        assert result.content

        text_blocks = [
            item.text
            for item in result.content
            if hasattr(item, "text")
        ]

        assert text_blocks

        payload = json.loads(text_blocks[0])

        assert payload["schema"] == "public"
        assert "tables" in payload

        print("\nDiscovered MCP tools:", sorted(tool_names))
        print("Database tables:", payload["tables"])

    finally:
        await manager.disconnect_all()
