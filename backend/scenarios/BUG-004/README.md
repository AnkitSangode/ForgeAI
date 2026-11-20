# BUG-004: Pagination validation

## Task for ForgeAI

Implement paginate(items, limit, offset): require limit 1..100 and offset >= 0; return the requested slice. Raise ValueError for invalid bounds.

## Run acceptance tests

```powershell
python -m pytest -q
```
