from pathlib import PurePosixPath

from forgeai.execution.exceptions import PatchApplicationError
from forgeai.execution.sandbox.base import SandboxProvider, SandboxSession
from forgeai.execution.schemas import GitRepositoryState


class GitStateCollector:
    """Collect a Git working-tree snapshot and hashes of changed files."""

    STATUS_COMMAND = "git status --porcelain=v1 -z --untracked-files=all"
    COMMAND_TIMEOUT_SECONDS = 30

    def __init__(self, sandbox_provider: SandboxProvider) -> None:
        self.sandbox_provider = sandbox_provider

    def capture(self, session: SandboxSession) -> GitRepositoryState:
        result = self.sandbox_provider.run_command(
            session,
            self.STATUS_COMMAND,
            self.COMMAND_TIMEOUT_SECONDS,
        )

        if result.exit_code != 0:
            raise PatchApplicationError("Unable to inspect repository state.")

        modified_files: set[str] = set()
        untracked_files: set[str] = set()
        deleted_files: set[str] = set()

        records = result.stdout.split("\x00")
        index = 0

        while index < len(records):
            record = records[index]
            index += 1

            if not record:
                continue

            if len(record) < 4 or record[2] != " ":
                raise PatchApplicationError("Git returned an invalid repository status.")

            status = record[:2]
            file_path = record[3:]

            # Rename and copy records contain an additional path.
            # Consume it before failing so the parser's format is explicit.
            if "R" in status or "C" in status:
                if index < len(records):
                    index += 1

                raise PatchApplicationError("Rename and copy changes are not supported.")

            if "U" in status:
                raise PatchApplicationError(
                    "Repositories with unresolved merge conflicts cannot be processed."
                )

            self._validate_path(file_path)

            if status == "??":
                untracked_files.add(file_path)
                continue

            if "D" in status:
                deleted_files.add(file_path)
                continue

            # Remaining supported tracked changes include modifications,
            # additions and file-type changes.
            if any(character in "MAT" for character in status):
                modified_files.add(file_path)
                continue

            raise PatchApplicationError("Git returned an unsupported file status.")

        file_hashes: list[tuple[str, str]] = []

        existing_changed_files = modified_files | untracked_files

        for file_path in sorted(existing_changed_files):
            if not self.sandbox_provider.file_exists(session, file_path):
                raise PatchApplicationError("A changed repository file could not be found.")

            file_result = self.sandbox_provider.read_file(
                session,
                file_path,
            )

            if not file_result.sha256:
                raise PatchApplicationError("Unable to calculate a changed file's hash.")

            file_hashes.append((file_path, file_result.sha256))

        return GitRepositoryState(
            modified_files=frozenset(modified_files),
            untracked_files=frozenset(untracked_files),
            deleted_files=frozenset(deleted_files),
            file_hashes=tuple(file_hashes),
        )

    @staticmethod
    def _validate_path(file_path: str) -> None:
        if not file_path or "\x00" in file_path or "\\" in file_path:
            raise PatchApplicationError("Git returned an invalid repository file path.")

        path = PurePosixPath(file_path)

        if (
            path.is_absolute()
            or not path.parts
            or any(part in {".", ".."} for part in path.parts)
            or str(path) != file_path
        ):
            raise PatchApplicationError("Git returned an unsafe repository file path.")
