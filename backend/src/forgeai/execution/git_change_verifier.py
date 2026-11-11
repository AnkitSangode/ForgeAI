from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.schemas import GitRepositoryState


class GitChangeVerifier:
    """Verify that execution changed exactly the authorized repository files."""

    def verify(
        self,
        baseline: GitRepositoryState,
        final_state: GitRepositoryState,
        expected_changes: list[CodeChange],
    ) -> None:
        if not expected_changes:
            raise PatchApplicationError("No expected changes were provided.")

        expected_paths = [change.file_path for change in expected_changes]

        if len(expected_paths) != len(set(expected_paths)):
            raise PatchApplicationError("Expected changes contain duplicate file paths.")

        baseline_files = self._build_file_state(baseline)
        final_files = self._build_file_state(final_state)

        all_paths = set(baseline_files) | set(final_files)

        actual_changed_paths = {
            path for path in all_paths if baseline_files.get(path) != final_files.get(path)
        }

        expected_path_set = set(expected_paths)

        unexpected_paths = actual_changed_paths - expected_path_set
        missing_paths = expected_path_set - actual_changed_paths

        if unexpected_paths:
            raise PatchApplicationError("Execution modified files outside the authorized patch.")

        if missing_paths:
            raise PatchApplicationError("Some expected repository changes were not detected.")

        self._verify_change_types(
            expected_changes=expected_changes,
            final_files=final_files,
        )

    @staticmethod
    def _verify_change_types(
        expected_changes: list[CodeChange],
        final_files: dict[str, tuple[str, str | None]],
    ) -> None:
        expected_status = {
            "create": "untracked",
            "modify": "modified",
            "delete": "deleted",
        }

        for change in expected_changes:
            expected_type = expected_status.get(change.change_type)

            if expected_type is None:
                raise PatchApplicationError(
                    f"Unsupported expected change type: {change.change_type}."
                )

            actual_status = final_files.get(change.file_path)

            if actual_status is None or actual_status[0] != expected_type:
                raise PatchApplicationError(
                    f"Repository change type does not match the expected "
                    f"'{change.change_type}' operation for '{change.file_path}'."
                )

    @staticmethod
    def _build_file_state(
        state: GitRepositoryState,
    ) -> dict[str, tuple[str, str | None]]:
        """Build a comparable status-and-hash representation."""

        modified = state.modified_files
        untracked = state.untracked_files
        deleted = state.deleted_files

        if modified & untracked or modified & deleted or untracked & deleted:
            raise PatchApplicationError(
                "Repository snapshot contains conflicting file classifications."
            )

        hashes = dict(state.file_hashes)

        if len(hashes) != len(state.file_hashes):
            raise PatchApplicationError("Repository snapshot contains duplicate file hashes.")

        existing_paths = modified | untracked

        if set(hashes) != existing_paths:
            raise PatchApplicationError("Repository snapshot contains incomplete file hashes.")

        file_state: dict[str, tuple[str, str | None]] = {}

        for path in modified:
            file_state[path] = ("modified", hashes[path])

        for path in untracked:
            file_state[path] = ("untracked", hashes[path])

        for path in deleted:
            file_state[path] = ("deleted", None)

        return file_state
