
from unittest.mock import Mock

import pytest

from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.git_change_verifier import GitChangeVerifier
from forgeai.execution.schemas import GitRepositoryState


@pytest.fixture
def verifier():
    return GitChangeVerifier()


def make_state(
    modified=(),
    untracked=(),
    deleted=(),
    hashes=(),
):
    return GitRepositoryState(
        modified_files=frozenset(modified),
        untracked_files=frozenset(untracked),
        deleted_files=frozenset(deleted),
        file_hashes=tuple(hashes),
    )


def make_change(path, change_type="modify"):
    return Mock(
        file_path=path,
        change_type=change_type,
    )


# ---------------------------------------------------------
# 1. Expected changes
# ---------------------------------------------------------


def test_accepts_expected_modified_file(verifier):
    baseline = make_state()
    final = make_state(
        modified={"src/auth.py"},
        hashes=[("src/auth.py", "b" * 64)],
    )

    verifier.verify(
        baseline,
        final,
        [make_change("src/auth.py", "modify")],
    )


def test_accepts_expected_created_file(verifier):
    baseline = make_state()
    final = make_state(
        untracked={"src/new.py"},
        hashes=[("src/new.py", "a" * 64)],
    )

    verifier.verify(
        baseline,
        final,
        [make_change("src/new.py", "create")],
    )


def test_accepts_expected_deleted_file(verifier):
    baseline = make_state()
    final = make_state(
        deleted={"src/old.py"},
    )

    verifier.verify(
        baseline,
        final,
        [make_change("src/old.py", "delete")],
    )


# ---------------------------------------------------------
# 2. Pre-existing changes
# ---------------------------------------------------------


def test_ignores_preexisting_change_when_hash_is_unchanged(verifier):
    baseline = make_state(
        modified={"src/config.py"},
        hashes=[("src/config.py", "a" * 64)],
    )

    final = make_state(
        modified={"src/config.py", "src/auth.py"},
        hashes=[
            ("src/config.py", "a" * 64),
            ("src/auth.py", "b" * 64),
        ],
    )

    verifier.verify(
        baseline,
        final,
        [make_change("src/auth.py", "modify")],
    )


def test_detects_preexisting_file_changed_again(verifier):
    baseline = make_state(
        modified={"src/config.py"},
        hashes=[("src/config.py", "a" * 64)],
    )

    final = make_state(
        modified={"src/config.py", "src/auth.py"},
        hashes=[
            ("src/config.py", "b" * 64),
            ("src/auth.py", "c" * 64),
        ],
    )

    with pytest.raises(
        PatchApplicationError,
        match="outside the authorized",
    ):
        verifier.verify(
            baseline,
            final,
            [make_change("src/auth.py", "modify")],
        )


# ---------------------------------------------------------
# 3. Unexpected changes
# ---------------------------------------------------------


def test_rejects_unexpected_modified_file(verifier):
    baseline = make_state()

    final = make_state(
        modified={"src/secret.py"},
        hashes=[("src/secret.py", "a" * 64)],
    )

    with pytest.raises(
        PatchApplicationError,
        match="outside the authorized",
    ):
        verifier.verify(
            baseline,
            final,
            [make_change("src/auth.py", "modify")],
        )


def test_detects_unexpected_deleted_file(verifier):
    baseline = make_state()

    final = make_state(
        deleted={"src/old.py"},
    )

    with pytest.raises(
        PatchApplicationError,
        match="outside the authorized",
    ):
        verifier.verify(
            baseline,
            final,
            [make_change("src/auth.py", "modify")],
        )


# ---------------------------------------------------------
# 4. Missing expected changes
# ---------------------------------------------------------


def test_rejects_missing_expected_change(verifier):
    baseline = make_state()
    final = make_state()

    with pytest.raises(
        PatchApplicationError,
        match="not detected",
    ):
        verifier.verify(
            baseline,
            final,
            [make_change("src/auth.py", "modify")],
        )


# ---------------------------------------------------------
# 5. Change type verification
# ---------------------------------------------------------


@pytest.mark.parametrize(
    ("expected_type", "actual_state"),
    [
        ("modify", make_state(untracked={"src/auth.py"}, hashes=[("src/auth.py", "a" * 64)])),
        ("create", make_state(modified={"src/auth.py"}, hashes=[("src/auth.py", "a" * 64)])),
        ("delete", make_state(modified={"src/auth.py"}, hashes=[("src/auth.py", "a" * 64)])),
    ],
)
def test_rejects_mismatched_change_type(
    verifier,
    expected_type,
    actual_state,
):
    with pytest.raises(
        PatchApplicationError,
        match="change type does not match",
    ):
        verifier.verify(
            make_state(),
            actual_state,
            [make_change("src/auth.py", expected_type)],
        )


def test_rejects_unsupported_change_type(verifier):
    baseline = make_state()
    final = make_state(
        modified={"src/auth.py"},
        hashes=[("src/auth.py", "a" * 64)],
    )

    with pytest.raises(
        PatchApplicationError,
        match="Unsupported expected change type",
    ):
        verifier.verify(
            baseline,
            final,
            [make_change("src/auth.py", "rename")],
        )


# ---------------------------------------------------------
# 6. Empty and duplicate expected changes
# ---------------------------------------------------------


def test_rejects_empty_expected_changes(verifier):
    with pytest.raises(
        PatchApplicationError,
        match="No expected changes",
    ):
        verifier.verify(
            make_state(),
            make_state(),
            [],
        )


def test_rejects_duplicate_expected_paths(verifier):
    with pytest.raises(
        PatchApplicationError,
        match="duplicate",
    ):
        verifier.verify(
            make_state(),
            make_state(),
            [
                make_change("src/auth.py", "modify"),
                make_change("src/auth.py", "modify"),
            ],
        )


# ---------------------------------------------------------
# 7. Snapshot validation
# ---------------------------------------------------------


def test_rejects_incomplete_snapshot_hashes(verifier):
    baseline = make_state(
        modified={"src/auth.py"},
        hashes=[],
    )

    with pytest.raises(
        PatchApplicationError,
        match="incomplete file hashes",
    ):
        verifier.verify(
            baseline,
            make_state(),
            [make_change("src/auth.py", "modify")],
        )


def test_rejects_duplicate_snapshot_hashes(verifier):
    baseline = make_state(
        modified={"src/auth.py"},
        hashes=[
            ("src/auth.py", "a" * 64),
            ("src/auth.py", "b" * 64),
        ],
    )

    with pytest.raises(
        PatchApplicationError,
        match="duplicate file hashes",
    ):
        verifier.verify(
            baseline,
            make_state(),
            [make_change("src/auth.py", "modify")],
        )


@pytest.mark.parametrize(
    "state",
    [
        make_state(
            modified={"src/auth.py"},
            untracked={"src/auth.py"},
            hashes=[("src/auth.py", "a" * 64)],
        ),
        make_state(
            modified={"src/auth.py"},
            deleted={"src/auth.py"},
            hashes=[("src/auth.py", "a" * 64)],
        ),
        make_state(
            untracked={"src/auth.py"},
            deleted={"src/auth.py"},
            hashes=[("src/auth.py", "a" * 64)],
        ),
    ],
)
def test_rejects_conflicting_snapshot_classifications(verifier, state):
    with pytest.raises(
        PatchApplicationError,
        match="conflicting file classifications",
    ):
        verifier.verify(
            state,
            make_state(),
            [make_change("src/auth.py", "modify")],
        )


def test_rejects_incomplete_final_snapshot_hashes(verifier):
    final = make_state(
        modified={"src/auth.py"},
        hashes=[],
    )

    with pytest.raises(
        PatchApplicationError,
        match="incomplete file hashes",
    ):
        verifier.verify(
            make_state(),
            final,
            [make_change("src/auth.py", "modify")],
        )
