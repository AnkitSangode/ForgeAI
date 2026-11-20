# BUG-012: Atomic in-memory update

## Task for ForgeAI

Implement apply_updates(state, updates): apply updates to a copy and return it; if any key is not a string or any value is None, raise ValueError and do not mutate the original state.

## Run acceptance tests

```powershell
python -m pytest -q
```
