
class MCPToolCallLimitExceeded(RuntimeError):
    """Raised when an MCP task exhausts its tool-call budget."""


class MCPToolExecutionBudget:
    """Tracks MCP tool calls for one task execution."""

    def __init__(self, max_calls: int = 10) -> None:
        if (
            isinstance(max_calls, bool)
            or not isinstance(max_calls, int)
            or max_calls <= 0
        ):
            raise ValueError("MCP tool-call limit must be a positive integer.")

        self._max_calls = max_calls
        self._calls_used = 0

    @property
    def max_calls(self) -> int:
        return self._max_calls

    @property
    def calls_used(self) -> int:
        return self._calls_used

    @property
    def remaining_calls(self) -> int:
        return self._max_calls - self._calls_used

    def consume(self) -> None:
        """Reserve one tool call before attempting execution."""

        if self._calls_used >= self._max_calls:
            raise MCPToolCallLimitExceeded(
                f"MCP tool-call budget exhausted. "
                f"Maximum allowed calls: {self._max_calls}."
            )

        self._calls_used += 1
