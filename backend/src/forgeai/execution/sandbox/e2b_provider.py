import hashlib
from pathlib import PurePosixPath

from e2b import Sandbox

from forgeai.core.config import Settings
from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxFileResult,
    SandboxProvider,
    SandboxSession,
)


class E2BSandboxProvider(SandboxProvider):
    """E2B-backed implementation of the sandbox contract."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.e2b_api_key.get_secret_value()
        self._timeout = settings.e2b_sandbox_timeout
        self._workspace_root = settings.e2b_workspace_root.rstrip("/")

        if not self._workspace_root.startswith("/"):
            raise ValueError("Sandbox workspace root must be absolute.")

    def _get_sandbox(self, session: SandboxSession) -> Sandbox:
        sandbox = session._handle

        if not isinstance(sandbox, Sandbox):
            raise TypeError("Invalid E2B sandbox session.")

        return sandbox

    def _resolve_path(
        self,
        file_path: str,
        *,
        allow_root: bool = False,
    ) -> str:
        """Resolve a safe relative path inside the workspace."""

        if not file_path or "\x00" in file_path:
            raise ValueError("File path cannot be empty or contain NUL.")

        if "\\" in file_path:
            raise ValueError("Only POSIX-style paths are supported.")

        relative_path = PurePosixPath(file_path)

        if relative_path.is_absolute():
            raise ValueError("Absolute file paths are not allowed.")

        if any(part in {".", ".."} for part in relative_path.parts):
            raise ValueError("Path traversal is not allowed.")

        if not relative_path.parts:
            if allow_root:
                return self._workspace_root
            raise ValueError("A file path is required.")

        return str(PurePosixPath(self._workspace_root) / relative_path)

    def create(self, timeout_seconds: int) -> SandboxSession:
        if timeout_seconds <= 0:
            raise ValueError("Sandbox timeout must be positive.")

        sandbox = Sandbox.create(
            api_key=self._api_key,
            timeout=timeout_seconds,
            allow_internet_access=True,
        )

        try:
            sandbox.files.make_dir(self._workspace_root)
        except Exception:
            sandbox.kill()
            raise

        return SandboxSession(
            sandbox_id=sandbox.sandbox_id,
            _handle=sandbox,
        )

    def run_command(
        self,
        session: SandboxSession,
        command: str,
        timeout_seconds: int,
    ) -> CommandExecutionResult:
        if not command.strip():
            raise ValueError("Command cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("Command timeout must be positive.")

        sandbox = self._get_sandbox(session)

        result = sandbox.commands.run(
            command,
            cwd=self._workspace_root,
            timeout=timeout_seconds,
        )

        return CommandExecutionResult(
            command=command,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def create_file(
        self,
        session: SandboxSession,
        file_path: str,
        content: str,
    ) -> SandboxFileResult:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(file_path)

        if sandbox.files.exists(remote_path):
            raise FileExistsError(file_path)

        sandbox.files.write(remote_path, content)

        return SandboxFileResult(file_path=file_path)

    def read_file(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> SandboxFileResult:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(file_path)

        content = sandbox.files.read(remote_path)

        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return SandboxFileResult(
            file_path=file_path,
            content=content,
            sha256=file_hash,
        )

    def write_file(
        self,
        session: SandboxSession,
        file_path: str,
        content: str,
    ) -> SandboxFileResult:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(file_path)

        if not sandbox.files.exists(remote_path):
            raise FileNotFoundError(file_path)

        sandbox.files.write(remote_path, content)

        return SandboxFileResult(file_path=file_path)

    def delete_file(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> None:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(file_path)

        if not sandbox.files.exists(remote_path):
            raise FileNotFoundError(file_path)

        sandbox.files.remove(remote_path)

    def file_exists(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> bool:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(file_path)

        return sandbox.files.exists(remote_path)

    def list_files(
        self,
        session: SandboxSession,
        directory_path: str,
    ) -> list[str]:
        sandbox = self._get_sandbox(session)
        remote_path = self._resolve_path(
            directory_path,
            allow_root=True,
        )

        entries = sandbox.files.list(remote_path, depth=1)

        return [entry.name for entry in entries]

    def is_running(self, session: SandboxSession) -> bool:
        sandbox = self._get_sandbox(session)
        return sandbox.is_running()

    def terminate(self, session: SandboxSession) -> None:
        sandbox = self._get_sandbox(session)
        sandbox.kill()
