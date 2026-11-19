
import pytest

from forgeai.application.mcp import (
    MCPToolCallLimitExceeded,
    MCPToolExecutionBudget,
)


def test_budget_starts_with_full_allowance():
    budget = MCPToolExecutionBudget(max_calls=5)

    assert budget.max_calls == 5
    assert budget.calls_used == 0
    assert budget.remaining_calls == 5


def test_budget_consumes_one_call():
    budget = MCPToolExecutionBudget(max_calls=5)

    budget.consume()

    assert budget.calls_used == 1
    assert budget.remaining_calls == 4


def test_budget_allows_calls_until_limit():
    budget = MCPToolExecutionBudget(max_calls=3)

    budget.consume()
    budget.consume()
    budget.consume()

    assert budget.calls_used == 3
    assert budget.remaining_calls == 0


def test_budget_rejects_calls_after_limit():
    budget = MCPToolExecutionBudget(max_calls=2)

    budget.consume()
    budget.consume()

    with pytest.raises(MCPToolCallLimitExceeded):
        budget.consume()

    assert budget.calls_used == 2


def test_rejected_call_does_not_consume_budget():
    budget = MCPToolExecutionBudget(max_calls=1)

    budget.consume()

    with pytest.raises(MCPToolCallLimitExceeded):
        budget.consume()

    assert budget.calls_used == 1
    assert budget.remaining_calls == 0


def test_each_budget_has_independent_counter():
    first_task = MCPToolExecutionBudget(max_calls=2)
    second_task = MCPToolExecutionBudget(max_calls=2)

    first_task.consume()
    first_task.consume()

    assert first_task.remaining_calls == 0
    assert second_task.remaining_calls == 2


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, 1.5, True, "10", None],
)
def test_budget_rejects_invalid_limits(invalid_limit):
    with pytest.raises(ValueError):
        MCPToolExecutionBudget(max_calls=invalid_limit)
