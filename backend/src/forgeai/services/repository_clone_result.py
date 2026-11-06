
from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryCloneResult:
    repository_name: str
    repository_path: str
    commit_sha: str
    remote_url: str
