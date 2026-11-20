from sqlalchemy.orm import Session

from forgeai.core.security import (
    create_access_token,
    verify_password,
    hash_password,
)
from forgeai.infrastructure.models.user import User
from forgeai.infrastructure.repositories.user_repository import UserRepository


class DuplicateEmailError(Exception):
    """Raised when an account already exists for an email address."""


class AuthenticationError(Exception):
    """Raised when user authentication fails."""


class AuthService:
    """Coordinates user authentication and access-token generation."""

    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def register(self, email: str, password: str) -> str:
        """Create a user account and return its access token."""
        normalized_email = email.strip().lower()
        if self.repository.get_by_email(normalized_email) is not None:
            raise DuplicateEmailError("An account with this email already exists.")

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
        )
        try:
            self.repository.create(user)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise

        return create_access_token(subject=str(user.id))

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
