
import asyncio
import json
import sys

from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig


async def test_web_search_mcp_server_discovers_and_executes_tools():
    manager = MCPClientManager()

    config = MCPServerConfig(
        name="web_search",
        command=sys.executable,
        args=(
            "-m",
            "forgeai.infrastructure.mcp.servers.web_search_server",
        ),
    )

    try:
        async with asyncio.timeout(30):
            await manager.connect(config)

        assert manager.is_connected("web_search")

        async with asyncio.timeout(30):
            tools = await manager.list_tools("web_search")

        tool_names = {tool.name for tool in tools}

        assert "search_web" in tool_names

        async with asyncio.timeout(60):
            result = await manager.call_tool(
                "web_search",
                "search_web",
                {
                    "query": "Python official documentation",
                    "max_results": 3,
                },
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

        assert payload["provider"] == "DuckDuckGo"
        assert payload["query"] == "Python official documentation"
        assert "results" in payload

        print("\nDiscovered tools:", sorted(tool_names))
        print("\nSearch results:", json.dumps(payload, indent=2))

    finally:
        await manager.disconnect_all()
