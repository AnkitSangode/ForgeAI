import pytest
from solution import normalize_email

def test_normalizes_email():
    assert normalize_email("  Alice@Example.COM  ") == "alice@example.com"

@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_rejects_invalid_email_values(value):
    with pytest.raises(ValueError):
        normalize_email(value)
