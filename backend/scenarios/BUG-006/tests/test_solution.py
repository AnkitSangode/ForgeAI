import pytest
from solution import can_transition

@pytest.mark.parametrize("current,target", [
    ("pending", "running"), ("pending", "cancelled"),
    ("running", "succeeded"), ("running", "failed"),
    ("running", "cancelled"), ("failed", "pending"),
])
def test_allowed_transitions(current, target):
    assert can_transition(current, target) is True

@pytest.mark.parametrize("current,target", [
    ("succeeded", "running"), ("cancelled", "pending"),
    ("pending", "succeeded"), ("running", "pending"),
    ("failed", "succeeded"), ("pending", "pending"),
])
def test_forbidden_transitions(current, target):
    assert can_transition(current, target) is False
