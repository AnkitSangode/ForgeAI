# BUG-007: UTC timestamp normalization

## Task for ForgeAI

Implement to_utc_iso(value): accept ISO datetime strings; treat naive timestamps as UTC; convert offset-aware timestamps to UTC; return ISO string ending in +00:00.

## Run acceptance tests

```powershell
python -m pytest -q
```
