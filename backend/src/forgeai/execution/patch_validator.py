from collections.abc import Iterable
from pathlib import PurePosixPath, PureWindowsPath
from typing import ClassVar

from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import PatchValidationError


class PatchValidator:
    """
    Performs structural and authorization validation of proposed code patches.

    This class deliberately does not inspect the repository filesystem.
    Filesystem checks belong to the execution provider (e.g. E2B).
    """

    _VALID_CHANGE_TYPES: ClassVar[frozenset[str]] = frozenset({"create", "modify", "delete"})

    def validate(
        self,
        changes: Iterable[CodeChange],
        allowed_paths: set[str],
    ) -> None:
        changes = list(changes)

        if not changes:
            raise PatchValidationError("At least one code change is required.")

        if not allowed_paths:
            raise PatchValidationError("The workflow has not authorized any target paths.")

        normalized_allowed_paths = {self._validate_relative_path(path) for path in allowed_paths}

        seen_paths: set[str] = set()

        for change in changes:
            if change.change_type not in self._VALID_CHANGE_TYPES:
                raise PatchValidationError(f"Unsupported change type: {change.change_type}")

            target_path = self._validate_relative_path(change.file_path)

            if target_path in seen_paths:
                raise PatchValidationError(f"Duplicate patch target: {target_path}")

            seen_paths.add(target_path)

            if target_path not in normalized_allowed_paths:
                raise PatchValidationError(f"Patch target is not authorized: {target_path}")

            self._validate_diff(change, target_path)

    @staticmethod
    def _validate_relative_path(file_path: str) -> str:
        if not isinstance(file_path, str) or not file_path.strip():
            raise PatchValidationError("File path cannot be blank.")

        if "\x00" in file_path or "\\" in file_path:
            raise PatchValidationError(f"Invalid repository file path: {file_path}")

        windows_path = PureWindowsPath(file_path)
        posix_path = PurePosixPath(file_path)

        if windows_path.is_absolute() or windows_path.drive or posix_path.is_absolute():
            raise PatchValidationError(f"Absolute paths are not permitted: {file_path}")

        if any(part in {"", ".", ".."} for part in file_path.split("/")):
            raise PatchValidationError(f"Invalid relative path: {file_path}")

        if posix_path.as_posix() != file_path:
            raise PatchValidationError(f"Path is not canonical: {file_path}")

        return file_path

    def _validate_diff(
        self,
        change: CodeChange,
        target_path: str,
    ) -> None:
        diff_lines = change.unified_diff.splitlines()

        if not diff_lines:
            raise PatchValidationError(f"Empty unified diff for: {target_path}")

        hunk_index = next(
            (index for index, line in enumerate(diff_lines) if line.startswith("@@ ")),
            None,
        )

        if hunk_index is None:
            raise PatchValidationError(f"Unified diff contains no hunks: {target_path}")

        # File headers must occur before the first hunk.
        header_lines = diff_lines[:hunk_index]

        old_headers = [line for line in header_lines if line.startswith("--- ")]
        new_headers = [line for line in header_lines if line.startswith("+++ ")]

        if len(old_headers) != 1 or len(new_headers) != 1:
            raise PatchValidationError(
                f"Unified diff must contain exactly one old and one new file header: {target_path}"
            )

        old_path = self._normalize_diff_header(old_headers[0][4:])
        new_path = self._normalize_diff_header(new_headers[0][4:])

        if change.change_type == "create":
            expected_old = "/dev/null"
            expected_new = target_path

        elif change.change_type == "delete":
            expected_old = target_path
            expected_new = "/dev/null"

        else:
            expected_old = target_path
            expected_new = target_path

        if old_path != expected_old or new_path != expected_new:
            raise PatchValidationError(
                f"Diff headers do not match the requested "
                f"{change.change_type} operation for: {target_path}"
            )

    @classmethod
    def _normalize_diff_header(cls, header: str) -> str:
        """
        Normalize a unified diff file header path.

        Supports:
            a/src/file.py
            b/src/file.py
            src/file.py
            /dev/null

        A timestamp after a tab is ignored.
        """

        header = header.split("\t", maxsplit=1)[0]

        if not header:
            raise PatchValidationError("Unified diff contains an empty file header.")

        if header == "/dev/null":
            return "/dev/null"

        if header.startswith(("a/", "b/")):
            header = header[2:]

        return cls._validate_relative_path(header)
