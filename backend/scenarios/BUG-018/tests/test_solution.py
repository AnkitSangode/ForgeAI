import pytest
from solution import truncate_text

def test_truncates_unicode_without_encoding_corruption():
    assert truncate_text("नमस्ते世界", 6) == "नमस्ते"

def test_negative_limit_rejected():
    with pytest.raises(ValueError):
        truncate_text("hello", -1)

def test_short_text_unchanged():
    assert truncate_text("hi", 10) == "hi"
