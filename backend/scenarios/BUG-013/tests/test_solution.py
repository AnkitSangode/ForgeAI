import pytest
from solution import update_if_version

def test_updates_matching_version():
    record = {"name": "old", "version": 2}
    result = update_if_version(record, 2, {"name": "new"})
    assert result == {"name": "new", "version": 3}

def test_rejects_conflict_without_mutation():
    record = {"name": "old", "version": 3}
    with pytest.raises(ValueError):
        update_if_version(record, 2, {"name": "new"})
    assert record == {"name": "old", "version": 3}
