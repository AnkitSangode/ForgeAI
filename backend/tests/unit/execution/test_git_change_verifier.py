
import pytest
from unittest.mock import Mock

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


def make_change(path):
    return Mock(file_path=path)


def test_accepts_expected_modified_file(verifier):
    baseline = make_state(
        modified={"src/auth.py"},
        hashes=[("src/auth.py", "a" * 64)],
    )
    final = make_state(
        modified={"src/auth.py"},
        hashes=[("src/auth.py", "b" * 64)],
    )

    verifier.verify(baseline, final, [make_change("src/auth.py")])


def test_ignores_preexisting_change_when_hash_is_unchanged(verifier):
    baseline = make_state(
        modified={"src/config.py"},
        hashes=[("src/config.py", "a" * 64)],
    )
    final = make_state(
        modified={"src/config.py"},
        hashes=[("src/config.py", "a" * 64)],
    )

    verifier.verify(
        baseline,
        final,
        [make_change("src/auth.py")],
    ) if False else None

    # The unchanged pre-existing file must not count as an execution change.
    # An actual expected change is included below.
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
        [make_change("src/auth.py")],
    )


def test_rejects_unexpected_modified_file(verifier):
    baseline = make_state()
    final = make_state(
        modified={"src/secret.py"},
        hashes=[("src/secret.py", "a" * 64)],
    )

    with pytest.raises(PatchApplicationError, match="outside the authorized"):
        verifier.verify(baseline, final, [make_change("src/auth.py")])


def test_rejects_missing_expected_change(verifier):
    baseline = make_state()
    final = make_state()

    with pytest.raises(PatchApplicationError, match="not detected"):
        verifier.verify(baseline, final, [make_change("src/auth.py")])


def test_detects_new_untracked_file(verifier):
    baseline = make_state()
    final = make_state(
        untracked={"src/new.py"},
        hashes=[("src/new.py", "a" * 64)],
    )

    verifier.verify(baseline, final, [make_change("src/new.py")])


def test_detects_unexpected_deleted_file(verifier):
    baseline = make_state()
    final = make_state(deleted={"src/old.py"})

    with pytest.raises(PatchApplicationError, match="outside the authorized"):
        verifier.verify(baseline, final, [make_change("src/auth.py")])


def test_detects_deleted_expected_file(verifier):
    baseline = make_state()
    final = make_state(deleted={"src/old.py"})

    verifier.verify(baseline, final, [make_change("src/old.py")])


def test_rejects_empty_expected_changes(verifier):
    with pytest.raises(PatchApplicationError, match="No expected changes"):
        verifier.verify(make_state(), make_state(), [])


def test_rejects_duplicate_expected_paths(verifier):
    with pytest.raises(PatchApplicationError, match="duplicate"):
        verifier.verify(
            make_state(),
            make_state(),
            [
                make_change("src/auth.py"),
                make_change("src/auth.py"),
            ],
        )


def test_rejects_incomplete_snapshot_hashes(verifier):
    baseline = make_state(
        modified={"src/auth.py"},
        hashes=[],
    )

    with pytest.raises(PatchApplicationError, match="incomplete file hashes"):
        verifier.verify(
            baseline,
            make_state(),
            [make_change("src/auth.py")],
        )
