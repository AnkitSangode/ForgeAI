from pathlib import Path

def resolve_workspace_path(root, user_path):
    return Path(root) / user_path
