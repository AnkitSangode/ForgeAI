# BUG-018: Unicode-safe truncation

## Task for ForgeAI

Implement truncate_text(text, max_chars): truncate by Unicode code points, return unchanged if within limit, reject negative limits.

## Run acceptance tests

```powershell
python -m pytest -q
```
