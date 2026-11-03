import pytest
from pydantic import ValidationError

from forgeai.agent.coder_schema import CodeChange


def test_code_change_accepts_valid_modification():
    change = CodeChange(
        file_path="src/auth.py",
        change_type="modify",
        unified_diff="@@ -1 +1 @@\n-old\n+new",
        explanation="Fix token expiration validation.",
    )

    assert change.file_path == "src/auth.py"
    assert change.change_type == "modify"


def test_code_change_accepts_valid_creation():
    change = CodeChange(
        file_path="tests/test_auth.py",
        change_type="create",
        unified_diff="--- /dev/null\n+++ b/tests/test_auth.py\n@@ -0,0 +1 @@\n+def test_auth(): pass",
        explanation="Add authentication tests.",
    )

    assert change.change_type == "create"


def test_code_change_rejects_blank_file_path():
    with pytest.raises(ValidationError):
        CodeChange(
            file_path="   ",
            change_type="modify",
            unified_diff="@@ -1 +1 @@\n-old\n+new",
            explanation="Fix token expiration validation.",
        )


def test_code_change_rejects_blank_explanation():
    with pytest.raises(ValidationError):
        CodeChange(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff="@@ -1 +1 @@\n-old\n+new",
            explanation="   ",
        )
