import pytest
from solution import safe_divide

def test_normal_division():
    assert safe_divide(8, 2) == 4

def test_zero_divisor_has_domain_error():
    with pytest.raises(ValueError, match="division by zero"):
        safe_divide(8, 0)
