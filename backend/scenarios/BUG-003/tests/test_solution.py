import pytest
from solution import parse_port

@pytest.mark.parametrize("value, expected", [("80", 80), (443, 443), ("65535", 65535)])
def test_valid_ports(value, expected):
    assert parse_port(value) == expected

@pytest.mark.parametrize("value", ["abc", "0", "-1", "65536", True, None])
def test_invalid_ports(value):
    with pytest.raises(ValueError):
        parse_port(value)
