
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from forgeai.application.mcp import (
    DiscoveredMCPTool,
    MCPConnectionService,
    MCPToolDiscoveryService,
    MCPToolExecutionBudget,
    MCPToolExecutionService,
)
from forgeai.application.mcp.mcp_tool_execution_service import (
    MCPToolOutputTooLargeError,
)
from forgeai.application.mcp.mcp_tool_policy import (
    MCPAuthorizationError,
    MCPToolPolicy,
)
from forgeai.infrastructure.mcp import MCPServerConfig


def make_policy() -> MCPToolPolicy:
    return MCPToolPolicy(
        allowed_servers=frozenset({"addition-server"}),
        allowed_tools={
            "addition-server": frozenset({"add_numbers"}),
        },
    )

def make_budget(max_calls: int = 10) -> MCPToolExecutionBudget:
    return MCPToolExecutionBudget(max_calls=max_calls)

def make_discovered_tool() -> DiscoveredMCPTool:
    return DiscoveredMCPTool(
        server_name="addition-server",
        name="add_numbers",
        description="Add two integers.",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
            "additionalProperties": False,
        },
    )


def make_mcp_tool(name: str, description: str, input_schema: dict):
    return SimpleNamespace(
        name=name,
        description=description,
        inputSchema=input_schema,
    )


@pytest.mark.asyncio
async def test_connection_service_connects_to_trusted_server():
    manager = AsyncMock()
    service = MCPConnectionService(
        client_manager=manager,
        policy=make_policy(),
    )

    config = MCPServerConfig(
        name="addition-server",
        command="python",
    )

    await service.connect(config)

    manager.connect.assert_awaited_once_with(config)


@pytest.mark.asyncio
async def test_connection_service_rejects_untrusted_server():
    manager = AsyncMock()
    service = MCPConnectionService(
        client_manager=manager,
        policy=make_policy(),
    )

    config = MCPServerConfig(
        name="untrusted-server",
        command="python",
    )

    with pytest.raises(MCPAuthorizationError):
        await service.connect(config)

    manager.connect.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_service_disconnects_server():
    manager = AsyncMock()
    service = MCPConnectionService(
        client_manager=manager,
        policy=make_policy(),
    )

    await service.disconnect("addition-server")

    manager.disconnect.assert_awaited_once_with("addition-server")


@pytest.mark.asyncio
async def test_discovery_service_discovers_and_registers_tools():
    manager = AsyncMock()
    manager.list_tools.return_value = [
        make_mcp_tool(
            name="add_numbers",
            description="Add two integers.",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        )
    ]

    service = MCPToolDiscoveryService(manager)

    tools = await service.discover("addition-server")

    assert len(tools) == 1
    assert tools[0].name == "add_numbers"
    assert tools[0].server_name == "addition-server"
    assert tools[0].description == "Add two integers."

    assert service.get_tool(
        "addition-server",
        "add_numbers",
    ) == tools[0]


@pytest.mark.asyncio
async def test_discovery_service_refresh_replaces_previous_tools():
    manager = AsyncMock()
    manager.list_tools.side_effect = [
        [
            make_mcp_tool(
                name="add_numbers",
                description="Add numbers.",
                input_schema={"type": "object"},
            )
        ],
        [
            make_mcp_tool(
                name="multiply_numbers",
                description="Multiply numbers.",
                input_schema={"type": "object"},
            )
        ],
    ]

    service = MCPToolDiscoveryService(manager)

    await service.discover("addition-server")
    refreshed = await service.discover("addition-server")

    assert [tool.name for tool in refreshed] == ["multiply_numbers"]
    assert service.get_tools("addition-server") == refreshed

    with pytest.raises(LookupError):
        service.get_tool("addition-server", "add_numbers")


@pytest.mark.asyncio
async def test_discovery_service_rejects_unknown_tool():
    manager = AsyncMock()
    service = MCPToolDiscoveryService(manager)

    with pytest.raises(LookupError):
        service.get_tool("addition-server", "unknown-tool")


@pytest.mark.asyncio
async def test_discovery_service_removes_server_tools():
    manager = AsyncMock()
    manager.list_tools.return_value = [
        make_mcp_tool(
            name="add_numbers",
            description="Add numbers.",
            input_schema={"type": "object"},
        )
    ]

    service = MCPToolDiscoveryService(manager)

    await service.discover("addition-server")
    service.remove_server("addition-server")

    assert service.get_tools("addition-server") == []

    with pytest.raises(LookupError):
        service.get_tool("addition-server", "add_numbers")


@pytest.mark.asyncio
async def test_execution_service_executes_valid_tool_arguments():
    manager = AsyncMock()
    manager.call_tool.return_value = "30"

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    result = await service.execute(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        budget=make_budget(),
    )

    assert result == "30"

    discovery.get_tool.assert_called_once_with(
        server_name="addition-server",
        tool_name="add_numbers",
    )

    manager.call_tool.assert_awaited_once_with(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
    )


@pytest.mark.asyncio
async def test_execution_service_rejects_invalid_arguments():
    manager = AsyncMock()
    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(ValueError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": "10", "b": 20},
            budget=make_budget(),
        )

    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_rejects_additional_arguments():
    manager = AsyncMock()
    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(ValueError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20, "unexpected": True},
            budget=make_budget(),
        )

    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_rejects_undiscovered_tool():
    manager = AsyncMock()
    discovery = Mock()
    discovery.get_tool.side_effect = LookupError("Tool not discovered.")

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(LookupError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=make_budget(),
        )

    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_rejects_non_dictionary_arguments():
    manager = AsyncMock()
    discovery = Mock()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(ValueError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments=["10", "20"],
            budget=make_budget(),
        )

    discovery.get_tool.assert_not_called()
    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_rejects_untrusted_server():
    manager = AsyncMock()
    discovery = Mock()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(MCPAuthorizationError):
        await service.execute(
            server_name="untrusted-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=make_budget(),
        )

    discovery.get_tool.assert_not_called()
    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_rejects_unauthorized_tool():
    manager = AsyncMock()
    discovery = Mock()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    with pytest.raises(MCPAuthorizationError):
        await service.execute(
            server_name="addition-server",
            tool_name="delete_everything",
            arguments={},
            budget=make_budget(),
        )

    discovery.get_tool.assert_not_called()
    manager.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_execution_service_times_out_when_tool_takes_too_long():
    manager = AsyncMock()

    async def slow_tool(**kwargs):
        await asyncio.sleep(1)

    manager.call_tool.side_effect = slow_tool

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
        timeout_seconds=0.05,
    )

    with pytest.raises(TimeoutError, match="execution timeout"):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=make_budget(),
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_zero_timeout():
    with pytest.raises(ValueError, match="greater than zero"):
        MCPToolExecutionService(
            client_manager=AsyncMock(),
            discovery_service=Mock(),
            policy=make_policy(),
            timeout_seconds=0,
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_negative_timeout():
    with pytest.raises(ValueError, match="greater than zero"):
        MCPToolExecutionService(
            client_manager=AsyncMock(),
            discovery_service=Mock(),
            policy=make_policy(),
            timeout_seconds=-1,
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_oversized_tool_output():
    manager = AsyncMock()
    manager.call_tool.return_value = "A" * 100

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
        max_output_bytes=50,
    )

    with pytest.raises(MCPToolOutputTooLargeError, match="exceeding"):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=make_budget(),
        )

    manager.call_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_execution_service_accepts_output_within_size_limit():
    manager = AsyncMock()
    manager.call_tool.return_value = "30"

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
        max_output_bytes=2,
    )

    result = await service.execute(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        budget=make_budget(),
    )

    assert result == "30"


@pytest.mark.asyncio
async def test_execution_service_accepts_empty_output():
    manager = AsyncMock()
    manager.call_tool.return_value = ""

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
        max_output_bytes=1,
    )

    result = await service.execute(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        budget=make_budget(),
    )

    assert result == ""


@pytest.mark.asyncio
async def test_execution_service_measures_utf8_output_bytes():
    manager = AsyncMock()
    manager.call_tool.return_value = "€€"

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
        max_output_bytes=5,
    )

    # Each euro symbol occupies 3 UTF-8 bytes.
    with pytest.raises(MCPToolOutputTooLargeError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=make_budget(),
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_zero_output_limit():
    with pytest.raises(ValueError, match="positive integer"):
        MCPToolExecutionService(
            client_manager=AsyncMock(),
            discovery_service=Mock(),
            policy=make_policy(),
            max_output_bytes=0,
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_negative_output_limit():
    with pytest.raises(ValueError, match="positive integer"):
        MCPToolExecutionService(
            client_manager=AsyncMock(),
            discovery_service=Mock(),
            policy=make_policy(),
            max_output_bytes=-100,
        )


@pytest.mark.asyncio
async def test_execution_service_rejects_non_integer_output_limit():
    with pytest.raises(ValueError, match="positive integer"):
        MCPToolExecutionService(
            client_manager=AsyncMock(),
            discovery_service=Mock(),
            policy=make_policy(),
            max_output_bytes=1.5,
        )


@pytest.mark.asyncio
async def test_execution_service_enforces_task_tool_call_limit():
    manager = AsyncMock()
    manager.call_tool.return_value = "30"

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    task_budget = make_budget(max_calls=2)

    for _ in range(2):
        result = await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=task_budget,
        )
        assert result == "30"

    from forgeai.application.mcp import MCPToolCallLimitExceeded

    with pytest.raises(MCPToolCallLimitExceeded):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=task_budget,
        )

    assert task_budget.calls_used == 2
    assert manager.call_tool.await_count == 2


@pytest.mark.asyncio
async def test_execution_service_keeps_task_budgets_independent():
    manager = AsyncMock()
    manager.call_tool.return_value = "30"

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    first_task_budget = make_budget(max_calls=1)
    second_task_budget = make_budget(max_calls=1)

    await service.execute(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        budget=first_task_budget,
    )

    await service.execute(
        server_name="addition-server",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        budget=second_task_budget,
    )

    assert first_task_budget.calls_used == 1
    assert second_task_budget.calls_used == 1
    assert manager.call_tool.await_count == 2


@pytest.mark.asyncio
async def test_execution_service_consumes_budget_when_tool_fails():
    manager = AsyncMock()
    manager.call_tool.side_effect = RuntimeError("MCP server failed")

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    budget = make_budget(max_calls=2)

    with pytest.raises(RuntimeError, match="MCP server failed"):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
            budget=budget,
        )

    assert budget.calls_used == 1
    assert budget.remaining_calls == 1


@pytest.mark.asyncio
async def test_execution_service_does_not_consume_budget_for_invalid_arguments():
    manager = AsyncMock()

    discovery = Mock()
    discovery.get_tool.return_value = make_discovered_tool()

    service = MCPToolExecutionService(
        client_manager=manager,
        discovery_service=discovery,
        policy=make_policy(),
    )

    budget = make_budget(max_calls=2)

    with pytest.raises(ValueError):
        await service.execute(
            server_name="addition-server",
            tool_name="add_numbers",
            arguments={"a": "invalid", "b": 20},
            budget=budget,
        )

    assert budget.calls_used == 0
    manager.call_tool.assert_not_awaited()
