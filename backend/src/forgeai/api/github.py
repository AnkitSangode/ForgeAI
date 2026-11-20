
import httpx

from fastapi import APIRouter, HTTPException, Query, Request


router = APIRouter(
    prefix="/api/v1/integrations/github",
    tags=["GitHub Integration"],
)


def get_github_service(request: Request):
    service = getattr(request.app.state, "github_service", None)

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="GitHub integration is not configured.",
        )

    return service


def handle_github_error(exc: Exception) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code

        if status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="GitHub authentication failed. Check your token.",
            )

        if status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="GitHub denied access. Check token permissions or rate limits.",
            )

        if status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="GitHub resource not found or inaccessible.",
            )

        raise HTTPException(
            status_code=502,
            detail="GitHub API returned an error.",
        )

    if isinstance(exc, httpx.RequestError):
        raise HTTPException(
            status_code=502,
            detail="Could not connect to GitHub.",
        )

    raise exc


@router.get("/me")
async def get_github_user(request: Request):
    service = get_github_service(request)

    try:
        user = await service.get_authenticated_user()

        return {
            "login": user.get("login"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
            "html_url": user.get("html_url"),
        }

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        handle_github_error(exc)


@router.get("/repositories")
async def list_github_repositories(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
):
    service = get_github_service(request)

    try:
        repositories = await service.list_repositories(
            page=page,
            per_page=per_page,
        )

        return {
            "page": page,
            "per_page": per_page,
            "count": len(repositories),
            "repositories": [
                {
                    "id": repository.get("id"),
                    "name": repository.get("name"),
                    "full_name": repository.get("full_name"),
                    "description": repository.get("description"),
                    "private": repository.get("private"),
                    "default_branch": repository.get("default_branch"),
                    "html_url": repository.get("html_url"),
                    "clone_url": repository.get("clone_url"),
                    "updated_at": repository.get("updated_at"),
                    "permissions": repository.get("permissions"),
                }
                for repository in repositories
            ],
        }

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        handle_github_error(exc)


@router.get("/repositories/{owner}/{repository}")
async def get_github_repository(
    owner: str,
    repository: str,
    request: Request,
):
    service = get_github_service(request)

    try:
        result = await service.get_repository(owner, repository)

        return {
            "id": result.get("id"),
            "name": result.get("name"),
            "full_name": result.get("full_name"),
            "private": result.get("private"),
            "default_branch": result.get("default_branch"),
            "html_url": result.get("html_url"),
            "clone_url": result.get("clone_url"),
            "description": result.get("description"),
            "permissions": result.get("permissions"),
        }

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        handle_github_error(exc)


@router.get("/repositories/{owner}/{repository}/branches")
async def list_github_branches(
    owner: str,
    repository: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
):
    service = get_github_service(request)

    try:
        branches = await service.list_branches(
            owner=owner,
            repository=repository,
            page=page,
            per_page=per_page,
        )

        return {
            "repository": f"{owner}/{repository}",
            "page": page,
            "per_page": per_page,
            "count": len(branches),
            "branches": [
                {
                    "name": branch.get("name"),
                    "commit_sha": branch.get("commit", {}).get("sha"),
                    "protected": branch.get("protected"),
                }
                for branch in branches
            ],
        }

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        handle_github_error(exc)
