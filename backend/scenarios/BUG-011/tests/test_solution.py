import pytest
from solution import is_retryable_status

@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 599])
def test_retryable(status):
    assert is_retryable_status(status) is True

@pytest.mark.parametrize("status", [200, 301, 400, 401, 403, 404])
def test_not_retryable(status):
    assert is_retryable_status(status) is False
