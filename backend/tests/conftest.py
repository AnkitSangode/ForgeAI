
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from forgeai.domain import Task
from forgeai.infrastructure.base import Base
from forgeai.infrastructure.session import get_db
from forgeai.main import app


def get_test_database_url() -> str:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    env_values = dotenv_values(env_path)

    url = (
        os.getenv("FORGEAI_TEST_DATABASE_URL")
        or env_values.get("FORGEAI_TEST_DATABASE_URL")
    )

    if not url:
        raise RuntimeError(
            "Set FORGEAI_TEST_DATABASE_URL in backend/.env "
            "to your dedicated forgeai_test database."
        )

    parsed_url = make_url(url)

    if parsed_url.database != "forge_ai_test":
        raise RuntimeError(
            "Integration tests may only use the forgeai_test database."
        )

    return url


@pytest.fixture(scope="session")
def test_engine():
    database_url = get_test_database_url()
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.begin() as connection:
            Base.metadata.create_all(connection)

        yield engine
    finally:
        with engine.begin() as connection:
            Base.metadata.drop_all(connection)

        engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(
        bind=test_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()

    try:
        yield session
    finally:
        session.rollback()
        session.execute(delete(Task))
        session.commit()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
