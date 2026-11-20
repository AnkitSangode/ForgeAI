# BUG-009: Archive member validation

## Task for ForgeAI

Implement is_safe_archive_member(name): return False for absolute paths, parent traversal, Windows drive paths, or NUL bytes; True for safe relative names.

## Run acceptance tests

```powershell
python -m pytest -q
```
