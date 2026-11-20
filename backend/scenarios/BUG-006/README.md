# BUG-006: Task status transitions

## Task for ForgeAI

Implement can_transition(current, target). Allowed transitions: pending->running/cancelled; running->succeeded/failed/cancelled; failed->pending. All others return False.

## Run acceptance tests

```powershell
python -m pytest -q
```
