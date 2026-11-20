from solution import to_utc_iso

def test_naive_timestamp_is_utc():
    assert to_utc_iso("2025-01-01T12:00:00") == "2025-01-01T12:00:00+00:00"

def test_offset_timestamp_converts_to_utc():
    assert to_utc_iso("2025-01-01T13:00:00+01:00") == "2025-01-01T12:00:00+00:00"
