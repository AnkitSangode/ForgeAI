
import asyncio
import json
import re
from collections.abc import Sequence
from typing import Any

from forgeai.application.mcp.mcp_execution_budget import (
    MCPToolExecutionBudget,
)
from forgeai.application.mcp.mcp_tool_discovery_service import (
    MCPToolDiscoveryService,
)
from forgeai.application.mcp.mcp_tool_execution_service import (
    MCPToolExecutionService,
)
from forgeai.llm.llm_service import LLMService
from forgeai.llm.tool_schemas import (
    LLMMessage,
    LLMToolCallResponse,
    LLMToolDefinition,
)


class MCPResearchService:
    """Coordinates LLM tool requests and MCP tool execution."""

    def __init__(
        self,
        llm_service: LLMService,
        discovery_service: MCPToolDiscoveryService,
        execution_service: MCPToolExecutionService,
        server_names: Sequence[str],
        max_rounds: int = 5,
    ) -> None:
        if not server_names:
            raise ValueError("At least one MCP server must be configured.")

        if max_rounds <= 0:
            raise ValueError("Maximum MCP research rounds must be positive.")

        self._llm_service = llm_service
        self._discovery_service = discovery_service
        self._execution_service = execution_service
        self._server_names = tuple(server_names)
        self._max_rounds = max_rounds

    async def research(
        self,
        prompt: str,
        budget: MCPToolExecutionBudget,
    ) -> LLMToolCallResponse:
        """Run the LLM-to-MCP tool-calling loop."""

        if not prompt.strip():
            raise ValueError("Research prompt cannot be empty.")

        if not isinstance(budget, MCPToolExecutionBudget):
            raise TypeError("A task-scoped MCP execution budget is required.")

        tools, tool_mapping = await self._discover_tools()

        if not tools:
            raise ValueError("No MCP tools are available for research.")

        messages = [
            LLMMessage(
                role="user",
                content=prompt,
            )
        ]

        for _ in range(self._max_rounds):
            # The Ollama SDK is synchronous. Keep it off the event loop.
            response = await asyncio.to_thread(
                self._llm_service.generate_with_tools,
                messages,
                tools,
            )

            if not response.tool_calls:
                if not response.content:
                    raise ValueError(
                        "LLM returned neither a final response nor tool calls."
                    )
                return response

            # Preserve the assistant's tool-call message in the conversation.
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            for requested_call in response.tool_calls:
                mapping = tool_mapping.get(requested_call.name)

                if mapping is None:
                    raise ValueError(
                        f"LLM requested an unknown tool: {requested_call.name}"
                    )

                server_name, original_tool_name = mapping

                result = await self._execution_service.execute(
                    server_name=server_name,
                    tool_name=original_tool_name,
                    arguments=requested_call.arguments,
                    budget=budget,
                )

                messages.append(
                    LLMMessage(
                        role="tool",
                        tool_name=requested_call.name,
                        content=self._serialize_tool_result(result),
                    )
                )

        raise RuntimeError(
            f"MCP research exceeded the maximum of {self._max_rounds} rounds."
        )

    async def _discover_tools(
        self,
    ) -> tuple[list[LLMToolDefinition], dict[str, tuple[str, str]]]:
        """Discover tools and create unique LLM-facing names."""

        definitions: list[LLMToolDefinition] = []
        mapping: dict[str, tuple[str, str]] = {}
        used_names: set[str] = set()

        for server_name in self._server_names:
            discovered_tools = await self._discovery_service.discover(
                server_name
            )

            for tool in discovered_tools:
                safe_server = re.sub(r"[^a-zA-Z0-9_]", "_", server_name)
                safe_tool = re.sub(r"[^a-zA-Z0-9_]", "_", tool.name)

                exposed_name = f"{safe_server}__{safe_tool}"

                if exposed_name in used_names:
                    raise ValueError(
                        f"Duplicate exposed MCP tool name: {exposed_name}"
                    )

                used_names.add(exposed_name)

                definitions.append(
                    LLMToolDefinition(
                        name=exposed_name,
                        description=tool.description or "",
                        parameters=tool.input_schema,
                    )
                )

                mapping[exposed_name] = (
                    server_name,
                    tool.name,
                )

        return definitions, mapping

    @staticmethod
    def _serialize_tool_result(result: Any) -> str:
        """Convert an MCP result into a conversation-safe string."""

        if hasattr(result, "model_dump"):
            payload = result.model_dump(mode="json")
        elif isinstance(result, (dict, list, str, int, float, bool)) or result is None:
            payload = result
        else:
            payload = str(result)

        return json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        )
