from datetime import datetime

def to_utc_iso(value):
    return datetime.fromisoformat(value).isoformat()
