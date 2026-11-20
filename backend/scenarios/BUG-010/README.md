# BUG-010: Bounded retry

## Task for ForgeAI

Implement retry_delay(attempt, base=0.5, maximum=8.0): attempt must be >=1; return min(base * 2**(attempt-1), maximum).

## Run acceptance tests

```powershell
python -m pytest -q
```
