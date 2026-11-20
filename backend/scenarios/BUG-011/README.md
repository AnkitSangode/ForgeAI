# BUG-011: Retryable HTTP status

## Task for ForgeAI

Implement is_retryable_status(status): true only for 408, 425, 429, and 500..599; false for all other HTTP status codes.

## Run acceptance tests

```powershell
python -m pytest -q
```
