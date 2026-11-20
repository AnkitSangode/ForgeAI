from datetime import datetime, timezone
from enum import Enum
from uuid import UUID
from solution import to_json_value

class State(Enum):
    READY = "ready"

def test_converts_supported_types():
    uid = UUID("12345678-1234-5678-1234-567812345678")
    stamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert to_json_value({"id": uid, "at": stamp, "state": State.READY}) == {
        "id": str(uid), "at": "2025-01-01T00:00:00+00:00", "state": "ready"
    }

def test_recurses_into_sequences():
    assert to_json_value((1, [2, 3])) == [1, [2, 3]]
