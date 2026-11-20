# BUG-008: Workspace path containment

## Task for ForgeAI

Implement resolve_workspace_path(root, user_path): resolve the path and ensure it remains inside root. Raise ValueError for traversal or absolute-path escape.

## Run acceptance tests

```powershell
python -m pytest -q
```
