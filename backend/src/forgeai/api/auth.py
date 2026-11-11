from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from forgeai.api.dependencies.auth import get_current_user
from forgeai.api.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from forgeai.application.auth_service import (
    AuthenticationError,
    AuthService,
)
from forgeai.infrastructure.models.user import User
from forgeai.infrastructure.session import get_db

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(db)

    try:
        access_token = service.authenticate(
            email=str(payload.email),
            password=payload.password,
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=str(current_user.id),
        email=current_user.email,
        is_active=current_user.is_active,
    )
