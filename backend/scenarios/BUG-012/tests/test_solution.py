import pytest
from solution import apply_updates

def test_returns_updated_copy():
    original = {"a": 1}
    result = apply_updates(original, {"b": 2})
    assert result == {"a": 1, "b": 2}
    assert original == {"a": 1}
    assert result is not original

def test_invalid_update_does_not_mutate_original():
    original = {"a": 1}
    with pytest.raises(ValueError):
        apply_updates(original, {"b": 2, "c": None})
    assert original == {"a": 1}
