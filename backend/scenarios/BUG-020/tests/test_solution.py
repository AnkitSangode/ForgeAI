import pytest
from solution import require_config

def test_returns_copy_when_complete():
    config = {"DATABASE_URL": "postgres://example", "JWT_SECRET": "not-empty"}
    result = require_config(config, ["DATABASE_URL", "JWT_SECRET"])
    assert result == config
    assert result is not config

def test_missing_or_empty_key_rejected_without_value_leak():
    config = {"DATABASE_URL": "postgres://example", "JWT_SECRET": ""}
    with pytest.raises(ValueError) as exc:
        require_config(config, ["DATABASE_URL", "JWT_SECRET", "E2B_API_KEY"])
    message = str(exc.value)
    assert "JWT_SECRET" in message
    assert "E2B_API_KEY" in message
    assert "postgres://example" not in message
