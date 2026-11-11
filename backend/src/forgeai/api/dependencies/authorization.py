from typing import Annotated

from fastapi import Depends, HTTPException, status

from forgeai.api.dependencies.auth import get_current_user
from forgeai.infrastructure.models.user import User, UserRole


def require_reviewer(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Allow only reviewers and administrators."""

    if current_user.role not in {
        UserRole.REVIEWER,
        UserRole.ADMIN,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    return current_user
