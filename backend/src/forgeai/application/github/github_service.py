
from forgeai.infrastructure.github.github_client import GitHubClient


class GitHubService:
    """Application-level GitHub integration operations."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    async def get_authenticated_user(self) -> dict:
        return await self.client.get_authenticated_user()

    async def get_repository(
        self,
        owner: str,
        repository: str,
    ) -> dict:
        return await self.client.get_repository(owner, repository)

    async def list_repositories(
        self,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        return await self.client.list_repositories(
            page=page,
            per_page=per_page,
        )

    async def list_branches(
        self,
        owner: str,
        repository: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        return await self.client.list_branches(
            owner=owner,
            repository=repository,
            page=page,
            per_page=per_page,
        )
