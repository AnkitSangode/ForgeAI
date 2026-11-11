import hashlib
import shlex

from forgeai.execution.repository_paths import (
    resolve_repository_file_path,
)
from forgeai.execution.sandbox.base import (
    SandboxProvider,
    SandboxSession,
)
from forgeai.services.repository_file_read_result import (
    RepositoryFileReadResult,
)

MAX_FILE_SIZE_BYTES = 100 * 1024


class SandboxRepositoryFileReader:
    """Reads repository files from a remote sandbox."""

    def __init__(
        self,
        sandbox_provider: SandboxProvider,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        if max_file_size_bytes <= 0:
            raise ValueError("Maximum file size must be positive.")

        self.sandbox_provider = sandbox_provider
        self.max_file_size_bytes = max_file_size_bytes

    def read(
        self,
        session: SandboxSession,
        repository_path: str,
        file_path: str,
    ) -> RepositoryFileReadResult:
        """Read a repository-relative file from the sandbox."""

        if repository_path != "repository":
            return self._unavailable(
                file_path,
                "Repository path must be the configured repository directory.",
            )

        try:
            remote_path = resolve_repository_file_path(file_path)

            # Confirm that the requested path is a regular file and not a
            # symbolic link before reading it.
            path_check = self.sandbox_provider.run_command(
                session=session,
                command=(
                    f"if [ -L {shlex.quote(remote_path)} ]; then "
                    "printf 'symlink'; "
                    f"elif [ -f {shlex.quote(remote_path)} ]; then "
                    "printf 'file'; "
                    "else printf 'unavailable'; fi"
                ),
                timeout_seconds=10,
            )

            if path_check.exit_code != 0:
                return self._unavailable(
                    file_path,
                    "Unable to inspect the requested repository file.",
                )

            file_type = path_check.stdout.strip()

            if file_type == "symlink":
                return self._unavailable(
                    file_path,
                    "Symbolic links are not supported.",
                )

            if file_type != "file":
                return self._unavailable(
                    file_path,
                    "Repository file does not exist or is not a regular file.",
                )

            # Check file size before downloading its contents.
            size_result = self.sandbox_provider.run_command(
                session=session,
                command=(f"wc -c < {shlex.quote(remote_path)}"),
                timeout_seconds=10,
            )

            if size_result.exit_code != 0:
                return self._unavailable(
                    file_path,
                    "Unable to determine repository file size.",
                )

            try:
                file_size = int(size_result.stdout.strip())
            except ValueError:
                return self._unavailable(
                    file_path,
                    "Sandbox returned an invalid file size.",
                )

            if file_size > self.max_file_size_bytes:
                return self._unavailable(
                    file_path,
                    f"File exceeds the {self.max_file_size_bytes}-byte limit.",
                )

            remote_file = self.sandbox_provider.read_file(
                session=session,
                file_path=remote_path,
            )

            if remote_file.content is None:
                return self._unavailable(
                    file_path,
                    "Sandbox returned no file content.",
                )

            content_bytes = remote_file.content.encode("utf-8")

            # Recheck after reading in case the file changed between the
            # size check and the read operation.
            if len(content_bytes) > self.max_file_size_bytes:
                return self._unavailable(
                    file_path,
                    f"File exceeds the {self.max_file_size_bytes}-byte limit.",
                )

            if len(content_bytes) != file_size:
                return self._unavailable(
                    file_path,
                    "File changed while it was being read.",
                )

            file_hash = hashlib.sha256(content_bytes).hexdigest()

            if remote_file.sha256 != file_hash:
                return self._unavailable(
                    file_path,
                    "Sandbox file hash verification failed.",
                )

            return RepositoryFileReadResult(
                status="available",
                file_path=file_path,
                content=remote_file.content,
                sha256=file_hash,
            )

        except UnicodeDecodeError:
            return self._unavailable(
                file_path,
                "Repository file is not valid UTF-8.",
            )

        except (OSError, RuntimeError, ValueError) as exc:
            return self._unavailable(
                file_path,
                f"Repository file read failed: {exc}",
            )

        except Exception as exc:
            # Convert provider/SDK failures into the existing result
            # contract instead of leaking provider-specific exceptions.
            return self._unavailable(
                file_path,
                f"Sandbox file read failed: {exc}",
            )

    @staticmethod
    def _unavailable(
        file_path: str,
        error: str,
    ) -> RepositoryFileReadResult:
        return RepositoryFileReadResult(
            status="unavailable",
            file_path=file_path,
            error=error,
        )
