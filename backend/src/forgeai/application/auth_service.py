from sqlalchemy.orm import Session

from forgeai.core.security import (
    create_access_token,
    verify_password,
)
from forgeai.infrastructure.repositories.user_repository import UserRepository


class AuthenticationError(Exception):
    """Raised when user authentication fails."""


class AuthService:
    """Coordinates user authentication and access-token generation."""

    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def authenticate(self, email: str, password: str) -> str:
        """Authenticate a user and return an access token."""

        user = self.repository.get_by_email(email)

        if user is None:
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("Invalid email or password.")

        return create_access_token(subject=str(user.id))
