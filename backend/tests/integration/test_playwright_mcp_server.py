
import asyncio

from forgeai.infrastructure.mcp import MCPClientManager
from forgeai.infrastructure.mcp.servers.playwright_server_config import (
    create_playwright_server_config,
)


async def test_playwright_mcp_server_discovers_and_executes_tools():
    manager = MCPClientManager()

    config = create_playwright_server_config()

    try:
        # 1. Launch the isolated browser MCP server.
        async with asyncio.timeout(60):
            await manager.connect(config)

        assert manager.is_connected("playwright")

        # 2. Discover available browser tools.
        async with asyncio.timeout(30):
            tools = await manager.list_tools("playwright")

        tool_names = {tool.name for tool in tools}

        assert "browser_navigate" in tool_names
        assert "browser_snapshot" in tool_names

        # 3. Navigate to a harmless public test page.
        async with asyncio.timeout(60):
            navigation_result = await manager.call_tool(
                "playwright",
                "browser_navigate",
                {"url": "https://example.com"},
            )

        assert not navigation_result.isError

        # 4. Inspect the page using the accessibility snapshot.
        async with asyncio.timeout(30):
            snapshot_result = await manager.call_tool(
                "playwright",
                "browser_snapshot",
                {},
            )

        assert not snapshot_result.isError
        assert snapshot_result.content

        text_blocks = [
            item.text
            for item in snapshot_result.content
            if hasattr(item, "text")
        ]

        assert text_blocks

        snapshot_text = "\n".join(text_blocks)

        assert "Example Domain" in snapshot_text

        print("\nDiscovered tools:", sorted(tool_names))
        print("\nBrowser snapshot:", snapshot_text[:2000])

    finally:
        await manager.disconnect_all()
