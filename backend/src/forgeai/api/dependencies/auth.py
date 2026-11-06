from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from forgeai.core.security import decode_access_token
from forgeai.infrastructure.models.user import User
from forgeai.infrastructure.repositories.user_repository import UserRepository
from forgeai.infrastructure.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from a verified access token."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise unauthorized from None

    repository = UserRepository(db)
    user = repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user
