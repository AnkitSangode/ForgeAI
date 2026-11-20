from solution import redact_secrets

def test_redacts_common_secret_fields():
    text = "api_key=abc123 token: xyz password=hunter2"
    result = redact_secrets(text)
    assert "abc123" not in result
    assert "xyz" not in result
    assert "hunter2" not in result
    assert result.count("[REDACTED]") == 3

def test_preserves_non_secret_text():
    result = redact_secrets("user=ankit status=ok")
    assert result == "user=ankit status=ok"
