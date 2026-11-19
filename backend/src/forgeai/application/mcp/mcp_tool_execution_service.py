
import asyncio
import json
import logging
import time
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from forgeai.application.mcp.mcp_execution_budget import (
    MCPToolExecutionBudget,
)
from forgeai.application.mcp.mcp_tool_discovery_service import (
    MCPToolDiscoveryService,
)
from forgeai.application.mcp.mcp_tool_policy import MCPToolPolicy
from forgeai.infrastructure.mcp import MCPClientManager


logger = logging.getLogger(__name__)


class MCPToolOutputTooLargeError(ValueError):
    """Raised when an MCP tool response exceeds the configured size limit."""


class MCPToolExecutionService:
    def __init__(
        self,
        client_manager: MCPClientManager,
        discovery_service: MCPToolDiscoveryService,
        policy: MCPToolPolicy,
        timeout_seconds: float = 30.0,
        max_output_bytes: int = 1_000_000,
        telemetry: Any | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("MCP tool timeout must be greater than zero.")

        if (
            isinstance(max_output_bytes, bool)
            or not isinstance(max_output_bytes, int)
            or max_output_bytes <= 0
        ):
            raise ValueError(
                "MCP tool output limit must be a positive integer."
            )

        self._client_manager = client_manager
        self._discovery_service = discovery_service
        self._policy = policy
        self._timeout_seconds = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._telemetry = telemetry

    async def execute(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        budget: MCPToolExecutionBudget,
    ) -> Any:
        """Execute one MCP tool call and record an independent telemetry span."""

        started_at = time.perf_counter()
        status = "success"

        if self._telemetry is None:
            return await self._execute(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                budget=budget,
            )

        try:
            with self._telemetry.span(
                name="mcp.tool.execute",
                input_data={
                    "server_name": server_name,
                    "tool_name": tool_name,
                },
                metadata={
                    "component": "mcp",
                    "server_name": server_name,
                    "tool_name": tool_name,
                },
            ) as observation:
                try:
                    result = await self._execute(
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments=arguments,
                        budget=budget,
                    )
                    return result
                except BaseException:
                    status = "error"
                    raise
                finally:
                    duration_ms = round(
                        (time.perf_counter() - started_at) * 1000,
                        2,
                    )

                    try:
                        observation.update(
                            output={
                                "status": status,
                                "duration_ms": duration_ms,
                            },
                            metadata={
                                "component": "mcp",
                                "server_name": server_name,
                                "tool_name": tool_name,
                                "status": status,
                                "duration_ms": duration_ms,
                            },
                        )
                    except Exception:
                        logger.warning(
                            "Failed to update MCP telemetry observation.",
                            exc_info=True,
                        )

        except Exception:
            # Telemetry must not turn a successful tool execution into failure.
            # Execution errors are still propagated by the inner block.
            raise

    async def _execute(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        budget: MCPToolExecutionBudget,
    ) -> Any:
        """Perform the actual MCP execution with existing safety checks."""

        if not isinstance(arguments, dict):
            raise ValueError("MCP tool arguments must be a dictionary.")

        if not isinstance(budget, MCPToolExecutionBudget):
            raise TypeError(
                "A task-scoped MCPToolExecutionBudget is required."
            )

        # 1. Authorize the server and tool.
        self._policy.authorize_tool(server_name, tool_name)

        # 2. Require a previously discovered tool.
        tool = self._discovery_service.get_tool(
            server_name=server_name,
            tool_name=tool_name,
        )

        # 3. Validate the tool's input schema before consuming budget.
        try:
            Draft202012Validator.check_schema(tool.input_schema)
            validator = Draft202012Validator(tool.input_schema)
            validator.validate(arguments)

        except ValidationError as exc:
            raise ValueError(
                f"Invalid arguments for MCP tool '{tool_name}': {exc.message}"
            ) from exc

        # 4. Reserve a call before contacting the MCP server.
        # Failed and timed-out executions still consume this reservation.
        budget.consume()

        # 5. Execute with a timeout.
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await self._client_manager.call_tool(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=arguments,
                )

        except TimeoutError as exc:
            raise TimeoutError(
                f"MCP tool '{tool_name}' on server '{server_name}' "
                f"exceeded the {self._timeout_seconds}-second execution timeout."
            ) from exc

        # 6. Enforce the maximum response size.
        output_size = self._measure_output_size(result)

        if output_size > self._max_output_bytes:
            raise MCPToolOutputTooLargeError(
                f"MCP tool '{tool_name}' on server '{server_name}' returned "
                f"{output_size} bytes, exceeding the "
                f"{self._max_output_bytes}-byte output limit."
            )

        return result

    @staticmethod
    def _measure_output_size(result: Any) -> int:
        """Measure the UTF-8 size of the serialized MCP response."""

        if isinstance(result, str):
            serialized = result
        elif hasattr(result, "model_dump"):
            serialized = json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        else:
            serialized = json.dumps(
                result,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        return len(serialized.encode("utf-8"))
