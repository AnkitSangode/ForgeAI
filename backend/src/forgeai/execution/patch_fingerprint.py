import hashlib
import json

from forgeai.agent.coder_schema import CodeChange


def generate_patch_fingerprint(
    changes: list[CodeChange],
) -> str:
    """Generate a deterministic fingerprint for proposed changes."""

    canonical_changes = [
        {
            "file_path": change.file_path,
            "change_type": change.change_type,
            "unified_diff": change.unified_diff,
        }
        for change in sorted(changes, key=lambda item: item.file_path)
    ]

    canonical_patch = json.dumps(
        canonical_changes,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(canonical_patch.encode("utf-8")).hexdigest()
