from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from forgeai.infrastructure.models.user import User


class UserRepository:
    """Handles database operations for user accounts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)

        return self.session.scalar(statement)

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()

        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)

        return self.session.scalar(statement)
