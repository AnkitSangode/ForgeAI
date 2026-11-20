# BUG-020: Required configuration validation

## Task for ForgeAI

Implement require_config(config, required_keys): return a copy when all keys exist and have non-empty values; otherwise raise ValueError listing missing keys without printing values.

## Run acceptance tests

```powershell
python -m pytest -q
```
