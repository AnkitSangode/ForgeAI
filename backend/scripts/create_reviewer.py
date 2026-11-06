import sys

from sqlalchemy import select

from forgeai.core.security import hash_password
from forgeai.infrastructure.models.user import User, UserRole
from forgeai.infrastructure.session import SessionLocal


def create_reviewer() -> None:
    email = input("Reviewer email: ").strip().lower()

    if not email:
        print("Email cannot be empty.")
        sys.exit(1)

    password = input("Reviewer password: ")
    confirmation = input("Confirm password: ")  

    if password != confirmation:
        print("Passwords do not match.")
        sys.exit(1)

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        sys.exit(1)

    with SessionLocal() as session:
        try:
            existing_user = session.scalar(
                select(User).where(User.email == email)
            )

            if existing_user is not None:
                print("An account with this email already exists.")
                sys.exit(1)

            reviewer = User(
                email=email,
                password_hash=hash_password(password),
                role=UserRole.REVIEWER,
                is_active=True,
            )

            session.add(reviewer)
            session.commit()

            print(f"Reviewer account created: {reviewer.email}")

        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    create_reviewer()