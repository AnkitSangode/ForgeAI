# BUG-015: Resource ownership authorization

## Task for ForgeAI

Implement can_access(resource_owner_id, current_user_id, is_admin=False): allow owner or admin only.

## Run acceptance tests

```powershell
python -m pytest -q
```
