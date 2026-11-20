# BUG-014: Secret redaction

## Task for ForgeAI

Implement redact_secrets(text): redact values after case-insensitive keys api_key, token, password, secret when followed by = or :. Preserve key and separator.

## Run acceptance tests

```powershell
python -m pytest -q
```
