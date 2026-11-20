# BUG-003: Port validation

## Task for ForgeAI

Implement parse_port(value): accept integer strings and integers from 1 through 65535; reject booleans, malformed values, zero, and out-of-range values with ValueError.

## Run acceptance tests

```powershell
python -m pytest -q
```
