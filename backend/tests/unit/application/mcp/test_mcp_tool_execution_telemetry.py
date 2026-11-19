
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from forgeai.application.mcp.mcp_execution_budget import (
    MCPToolExecutionBudget,
)
from forgeai.application.mcp.mcp_tool_discovery_service import (
    DiscoveredMCPTool,
)
from forgeai.application.mcp.mcp_tool_execution_service import (
    MCPToolExecutionService,
)
from forgeai.application.mcp.mcp_tool_policy import MCPToolPolicy


class FakeTelemetry:
    """Captures telemetry observations without contacting Langfuse."""

    def __init__(self):
        self.observations = []

    @contextmanager
    def span(self, *, name, input_data, metadata=None):
        observation = MagicMock()

        self.observations.append(
            {
                "name": name,
                "input_data": input_data,
                "metadata": metadata or {},
                "observation": observation,
            }
        )

        yield observation


@pytest.fixture
def mcp_dependencies():
    server_tools = {
        "postgres": "read_records",
        "filesystem": "read_file",
        "web_search": "search_web",
        "playwright": "browser_snapshot",
    }

    policy = MCPToolPolicy(
        allowed_servers=frozenset(server_tools),
        allowed_tools={
            server: frozenset({tool})
            for server, tool in server_tools.items()
        },
    )

    client_manager = MagicMock()
    client_manager.call_tool = AsyncMock(
        return_value={"content": "Test result"}
    )

    discovery_service = MagicMock()

    def get_tool(server_name, tool_name):
        return DiscoveredMCPTool(
            server_name=server_name,
            name=tool_name,
            description="Test MCP tool",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        )

    discovery_service.get_tool.side_effect = get_tool

    telemetry = FakeTelemetry()

    service = MCPToolExecutionService(
        client_manager=client_manager,
        discovery_service=discovery_service,
        policy=policy,
        timeout_seconds=5,
        max_output_bytes=10_000,
        telemetry=telemetry,
    )

    return {
        "service": service,
        "client_manager": client_manager,
        "telemetry": telemetry,
        "server_tools": server_tools,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("server_name", "tool_name"),
    [
        ("postgres", "read_records"),
        ("filesystem", "read_file"),
        ("web_search", "search_web"),
        ("playwright", "browser_snapshot"),
    ],
)
async def test_mcp_tool_execution_creates_individual_observation(
    mcp_dependencies,
    server_name,
    tool_name,
):
    dependencies = mcp_dependencies
    service = dependencies["service"]
    telemetry = dependencies["telemetry"]

    result = await service.execute(
        server_name=server_name,
        tool_name=tool_name,
        arguments={},
        budget=MCPToolExecutionBudget(max_calls=5),
    )

    assert result == {"content": "Test result"}

    assert len(telemetry.observations) == 1

    recorded = telemetry.observations[0]

    assert recorded["name"] == "mcp.tool.execute"
    assert recorded["input_data"] == {
        "server_name": server_name,
        "tool_name": tool_name,
    }

    observation = recorded["observation"]

    observation.update.assert_called_once()

    update_data = observation.update.call_args.kwargs

    assert update_data["output"]["status"] == "success"
    assert update_data["output"]["duration_ms"] >= 0

    assert update_data["metadata"]["server_name"] == server_name
    assert update_data["metadata"]["tool_name"] == tool_name


@pytest.mark.asyncio
async def test_mcp_tool_execution_records_failure(
    mcp_dependencies,
):
    dependencies = mcp_dependencies
    service = dependencies["service"]
    telemetry = dependencies["telemetry"]

    dependencies["client_manager"].call_tool.side_effect = RuntimeError(
        "Simulated MCP server failure"
    )

    with pytest.raises(RuntimeError, match="Simulated MCP server failure"):
        await service.execute(
            server_name="postgres",
            tool_name="read_records",
            arguments={},
            budget=MCPToolExecutionBudget(max_calls=5),
        )

    assert len(telemetry.observations) == 1

    observation = telemetry.observations[0]["observation"]
    update_data = observation.update.call_args.kwargs

    assert update_data["output"]["status"] == "error"
    assert update_data["output"]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_mcp_tool_execution_records_timeout(
    mcp_dependencies,
):
    dependencies = mcp_dependencies
    service = dependencies["service"]
    telemetry = dependencies["telemetry"]

    async def slow_tool(**kwargs):
        import asyncio

        await asyncio.sleep(1)

    dependencies["client_manager"].call_tool.side_effect = slow_tool

    # Replace the service with a short timeout.
    service._timeout_seconds = 0.01

    with pytest.raises(TimeoutError):
        await service.execute(
            server_name="postgres",
            tool_name="read_records",
            arguments={},
            budget=MCPToolExecutionBudget(max_calls=5),
        )

    assert len(telemetry.observations) == 1

    update_data = (
        telemetry.observations[0]["observation"].update.call_args.kwargs
    )

    assert update_data["output"]["status"] == "error"


@pytest.mark.asyncio
async def test_mcp_tool_execution_rejects_oversized_output(
    mcp_dependencies,
):
    dependencies = mcp_dependencies
    telemetry = dependencies["telemetry"]

    dependencies["client_manager"].call_tool.return_value = {
        "content": "x" * 100
    }

    dependencies["service"]._max_output_bytes = 10

    with pytest.raises(ValueError, match="exceeding"):
        await dependencies["service"].execute(
            server_name="postgres",
            tool_name="read_records",
            arguments={},
            budget=MCPToolExecutionBudget(max_calls=5),
        )

    update_data = telemetry.observations[0][
        "observation"
    ].update.call_args.kwargs

    assert update_data["output"]["status"] == "error"


@pytest.mark.asyncio
async def test_mcp_telemetry_does_not_record_raw_arguments(
    mcp_dependencies,
):
    dependencies = mcp_dependencies
    telemetry = dependencies["telemetry"]

    secret_arguments = {
        "password": "sensitive-test-password",
    }

    # This tool's schema accepts no arguments, so the validation should fail.
    with pytest.raises(ValueError, match="Invalid arguments"):
        await dependencies["service"].execute(
            server_name="postgres",
            tool_name="read_records",
            arguments=secret_arguments,
            budget=MCPToolExecutionBudget(max_calls=5),
        )

    recorded = telemetry.observations[0]

    assert "password" not in str(recorded["input_data"])
    assert "sensitive-test-password" not in str(recorded)
