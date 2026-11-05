import pytest
from pydantic import ValidationError

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import PatchValidationError
from forgeai.execution.patch_validator import PatchValidator


@pytest.fixture
def validator() -> PatchValidator:
    return PatchValidator()


def make_change(
    file_path: str = "src/auth.py",
    change_type: str = "modify",
    old_header: str = "a/src/auth.py",
    new_header: str = "b/src/auth.py",
) -> CodeChange:
    diff = f"--- {old_header}\n+++ {new_header}\n@@ -1,2 +1,2 @@\n-old_value = 1\n+new_value = 2\n"

    return CodeChange(
        file_path=file_path,
        change_type=change_type,
        unified_diff=diff,
        explanation="Update the authentication implementation.",
    )


class TestPatchValidator:
    def test_valid_modify_patch(self, validator):
        change = make_change()

        validator.validate(
            changes=[change],
            allowed_paths={"src/auth.py"},
        )

    def test_valid_create_patch(self, validator):
        change = make_change(
            file_path="src/new_module.py",
            change_type="create",
            old_header="/dev/null",
            new_header="b/src/new_module.py",
        )

        validator.validate(
            changes=[change],
            allowed_paths={"src/new_module.py"},
        )

    def test_valid_delete_patch(self, validator):
        change = make_change(
            file_path="src/old_module.py",
            change_type="delete",
            old_header="a/src/old_module.py",
            new_header="/dev/null",
        )

        validator.validate(
            changes=[change],
            allowed_paths={"src/old_module.py"},
        )

    @pytest.mark.parametrize("file_path", ["", " "])
    def test_code_change_rejects_blank_file_path(self, file_path):
        with pytest.raises(ValidationError):
            make_change(file_path=file_path)

    def test_valid_patch_does_not_require_local_repository(self, validator):
        change = make_change()

        # No repository_root or local filesystem is needed.
        validator.validate(
            changes=[change],
            allowed_paths={"src/auth.py"},
        )

    def test_rejects_empty_changes(self, validator):
        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_empty_allowed_paths(self, validator):
        change = make_change()

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths=set(),
            )

    @pytest.mark.parametrize(
        "file_path",
        [
            "../secret.py",
            "src/../secret.py",
            "./src/auth.py",
            "/etc/passwd",
            r"C:\Windows\system.ini",
            r"src\auth.py",
            "src//auth.py",
            "src/\x00auth.py",
        ],
    )
    def test_rejects_unsafe_paths(self, validator, file_path):
        change = make_change(file_path=file_path)

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={file_path},
            )

    def test_rejects_unauthorized_path(self, validator):
        change = make_change(file_path="src/auth.py")

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={"src/config.py"},
            )

    def test_rejects_duplicate_targets(self, validator):
        first = make_change()
        second = make_change()

        with pytest.raises(
            PatchValidationError,
            match="Duplicate patch target",
        ):
            validator.validate(
                changes=[first, second],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_missing_hunk(self, validator):
        change = CodeChange(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff=("--- a/src/auth.py\n+++ b/src/auth.py\n-old\n+new\n"),
            explanation="Update authentication logic.",
        )

        with pytest.raises(
            PatchValidationError,
            match="no hunks",
        ):
            validator.validate(
                changes=[change],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_missing_file_headers(self, validator):
        change = CodeChange(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff=("@@ -1 +1 @@\n-old\n+new\n"),
            explanation="Update authentication logic.",
        )

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_multiple_file_headers(self, validator):
        change = CodeChange(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff=(
                "--- a/src/auth.py\n"
                "--- a/src/other.py\n"
                "+++ b/src/auth.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
            explanation="Update authentication logic.",
        )

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_mismatched_modify_headers(self, validator):
        change = make_change(
            old_header="a/src/other.py",
            new_header="b/src/auth.py",
        )

        with pytest.raises(
            PatchValidationError,
            match="Diff headers do not match",
        ):
            validator.validate(
                changes=[change],
                allowed_paths={"src/auth.py"},
            )

    def test_rejects_wrong_create_headers(self, validator):
        change = make_change(
            file_path="src/new_module.py",
            change_type="create",
            old_header="a/src/new_module.py",
            new_header="b/src/new_module.py",
        )

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={"src/new_module.py"},
            )

    def test_rejects_wrong_delete_headers(self, validator):
        change = make_change(
            file_path="src/old_module.py",
            change_type="delete",
            old_header="a/src/old_module.py",
            new_header="b/src/old_module.py",
        )

        with pytest.raises(PatchValidationError):
            validator.validate(
                changes=[change],
                allowed_paths={"src/old_module.py"},
            )

    def test_accepts_diff_header_with_timestamp(self, validator):
        change = make_change(
            old_header="a/src/auth.py\t2026-11-05 10:00:00",
            new_header="b/src/auth.py\t2026-11-05 10:00:00",
        )

        validator.validate(
            changes=[change],
            allowed_paths={"src/auth.py"},
        )
