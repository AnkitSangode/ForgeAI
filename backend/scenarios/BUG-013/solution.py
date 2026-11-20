def update_if_version(record, expected_version, changes):
    record.update(changes)
    record["version"] = record.get("version", 0) + 1
    return record
