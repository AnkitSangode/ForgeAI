import pytest
from solution import retry_delay

def test_exponential_backoff():
    assert retry_delay(1) == 0.5
    assert retry_delay(2) == 1.0
    assert retry_delay(3) == 2.0

def test_caps_delay():
    assert retry_delay(10) == 8.0

@pytest.mark.parametrize("attempt", [0, -1])
def test_rejects_invalid_attempt(attempt):
    with pytest.raises(ValueError):
        retry_delay(attempt)
