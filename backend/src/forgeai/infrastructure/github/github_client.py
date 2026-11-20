
import httpx
from pydantic import SecretStr


class GitHubClient:
    """Async client for communicating with the GitHub REST API."""

    def __init__(
        self,
        token: SecretStr,
        base_url: str = "https://api.github.com",
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token.get_secret_value()}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def get_authenticated_user(self) -> dict:
        response = await self._client.get("/user")
        response.raise_for_status()
        return response.json()

    async def get_repository(
        self,
        owner: str,
        repository: str,
    ) -> dict:
        response = await self._client.get(
            f"/repos/{owner}/{repository}"
        )
        response.raise_for_status()
        return response.json()

    async def list_repositories(
        self,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        response = await self._client.get(
            "/user/repos",
            params={
                "visibility": "all",
                "affiliation": "owner,collaborator,organization_member",
                "sort": "updated",
                "direction": "desc",
                "page": page,
                "per_page": per_page,
            },
        )
        response.raise_for_status()
        return response.json()

    async def list_branches(
        self,
        owner: str,
        repository: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        response = await self._client.get(
            f"/repos/{owner}/{repository}/branches",
            params={
                "page": page,
                "per_page": per_page,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
