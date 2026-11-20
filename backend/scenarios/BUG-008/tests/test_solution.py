import pytest
from pathlib import Path
from solution import resolve_workspace_path

def test_resolves_safe_relative_path(tmp_path):
    result = resolve_workspace_path(tmp_path, "src/main.py")
    assert result == (tmp_path / "src/main.py").resolve()

@pytest.mark.parametrize("path", ["../secret.txt", "/etc/passwd", "src/../../secret"])
def test_rejects_escape(tmp_path, path):
    with pytest.raises(ValueError):
        resolve_workspace_path(tmp_path, path)
