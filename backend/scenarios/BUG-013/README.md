# BUG-013: Optimistic version check

## Task for ForgeAI

Implement update_if_version(record, expected_version, changes): update and increment version only when versions match; otherwise raise ValueError. Do not mutate on conflict.

## Run acceptance tests

```powershell
python -m pytest -q
```
