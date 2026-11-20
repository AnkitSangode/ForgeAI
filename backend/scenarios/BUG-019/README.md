# BUG-019: Guaranteed resource cleanup

## Task for ForgeAI

Implement use_resource(resource, operation): call operation(resource), and always call resource.close() exactly once, including when operation raises; return operation result.

## Run acceptance tests

```powershell
python -m pytest -q
```
