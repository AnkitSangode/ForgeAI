import pytest
from solution import safe_average

def test_average_values():
    assert safe_average([2, 4, 6]) == 4

def test_empty_values_return_none():
    assert safe_average([]) is None
