from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SandboxSession:
    """Represents one sandbox execution session."""

    sandbox_id: str
    _handle: Any = field(repr=False, compare=False)


@dataclass(frozen=True)
class CommandExecutionResult:
    """Result of a command executed inside a sandbox."""

    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class SandboxFileResult:
    """Result of a sandbox file operation."""

    file_path: str
    content: str | None = None
    sha256: str | None = None


class SandboxProvider(ABC):
    """Provider-independent contract for remote code execution."""

    @abstractmethod
    def create(
        self,
        timeout_seconds: int,
    ) -> SandboxSession:
        """Create a new sandbox session."""
        raise NotImplementedError

    @abstractmethod
    def connect(self, sandbox_id: str) -> SandboxSession:
        """Reconnect to an existing sandbox."""
        raise NotImplementedError

    @abstractmethod
    def run_command(
        self,
        session: SandboxSession,
        command: str,
        timeout_seconds: int,
    ) -> CommandExecutionResult:
        """Execute a command inside the sandbox."""
        raise NotImplementedError

    @abstractmethod
    def is_running(self, session: SandboxSession) -> bool:
        """Check whether the sandbox is running."""
        raise NotImplementedError

    @abstractmethod
    def terminate(self, session: SandboxSession) -> None:
        """Terminate the sandbox."""
        raise NotImplementedError

    @abstractmethod
    def file_exists(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> bool:
        """Check whether a remote file exists."""
        raise NotImplementedError

    @abstractmethod
    def create_file(
        self,
        session: SandboxSession,
        file_path: str,
        content: str,
    ) -> SandboxFileResult:
        """Create a new file. Fail if it already exists."""
        raise NotImplementedError

    @abstractmethod
    def read_file(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> SandboxFileResult:
        """Read an existing file and return its content and hash."""
        raise NotImplementedError

    @abstractmethod
    def write_file(
        self,
        session: SandboxSession,
        file_path: str,
        content: str,
    ) -> SandboxFileResult:
        """Write or replace an existing file."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(
        self,
        session: SandboxSession,
        file_path: str,
    ) -> None:
        """Delete an existing file."""
        raise NotImplementedError

    @abstractmethod
    def list_files(
        self,
        session: SandboxSession,
        directory_path: str,
    ) -> list[str]:
        """List entries in a directory."""
        raise NotImplementedError
