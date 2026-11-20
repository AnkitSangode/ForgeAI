# BUG-016: JSON-safe serialization

## Task for ForgeAI

Implement to_json_value(value): convert UUID to string, datetime to ISO string, Enum to its value, recursively handle dict/list/tuple, and leave JSON primitives unchanged.

## Run acceptance tests

```powershell
python -m pytest -q
```
