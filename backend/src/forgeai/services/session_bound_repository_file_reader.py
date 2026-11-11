from forgeai.execution.sandbox.base import SandboxSession
from forgeai.services.repository_file_read_result import (
    RepositoryFileReadResult,
)
from forgeai.services.sandbox_repository_file_reader import (
    SandboxRepositoryFileReader,
)


class SessionBoundRepositoryFileReader:
    """Adapts a sandbox reader to the context builder interface."""

    def __init__(
        self,
        sandbox_reader: SandboxRepositoryFileReader,
        session: SandboxSession,
    ) -> None:
        self.sandbox_reader = sandbox_reader
        self.session = session

    def read(
        self,
        repository_path: str,
        file_path: str,
    ) -> RepositoryFileReadResult:
        return self.sandbox_reader.read(
            session=self.session,
            repository_path=repository_path,
            file_path=file_path,
        )
