
import pytest

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.patch_builder import PatchBuilder


@pytest.fixture
def first_change():
    return CodeChange(
        file_path="src/app.py",
        change_type="modify",
        unified_diff=(
            "--- a/src/app.py\n"
            "+++ b/src/app.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        ),
        explanation="Update application implementation.",
    )


@pytest.fixture
def second_change():
    return CodeChange(
        file_path="src/config.py",
        change_type="modify",
        unified_diff=(
            "--- a/src/config.py\n"
            "+++ b/src/config.py\n"
            "@@ -1 +1 @@\n"
            "-DEBUG = False\n"
            "+DEBUG = True\n"
        ),
        explanation="Enable application debugging.",
    )


def test_build_single_change(first_change):
    patch = PatchBuilder.build([first_change])

    assert patch == first_change.unified_diff


def test_build_multiple_changes(first_change, second_change):
    patch = PatchBuilder.build([first_change, second_change])

    expected = (
        first_change.unified_diff.rstrip("\n")
        + "\n"
        + second_change.unified_diff.rstrip("\n")
        + "\n"
    )

    assert patch == expected


def test_build_removes_extra_trailing_newlines(first_change):
    first_change = first_change.model_copy(
        update={
            "unified_diff": first_change.unified_diff + "\n\n"
        }
    )

    patch = PatchBuilder.build([first_change])

    assert patch.endswith("\n")
    assert not patch.endswith("\n\n")


def test_build_rejects_empty_changes():
    with pytest.raises(
        PatchApplicationError,
        match="without code changes",
    ):
        PatchBuilder.build([])
