import pytest
from solution import is_safe_archive_member

@pytest.mark.parametrize("name", ["src/main.py", "data/file.txt", "README.md"])
def test_safe_members(name):
    assert is_safe_archive_member(name) is True

@pytest.mark.parametrize("name", ["../escape", "/etc/passwd", "C:\\Windows\\x", "a/../../b", "bad\x00name"])
def test_unsafe_members(name):
    assert is_safe_archive_member(name) is False
