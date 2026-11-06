from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from forgeai.application import auth_service
from forgeai.application.auth_service import (
    AuthenticationError,
    AuthService,
)


@pytest.fixture
def user():
    return SimpleNamespace(
        id=uuid4(),
        email="reviewer@forgeai.local",
        password_hash="$argon2id$test-hash",
        is_active=True,
    )


@pytest.fixture
def service(monkeypatch):
    repository = Mock()

    monkeypatch.setattr(
        auth_service,
        "UserRepository",
        lambda session: repository,
    )

    instance = AuthService(session=Mock())

    return instance, repository


def test_authenticate_returns_access_token(
    service,
    user,
    monkeypatch,
):
    instance, repository = service
    repository.get_by_email.return_value = user

    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda password, hashed: True,
    )

    monkeypatch.setattr(
        auth_service,
        "create_access_token",
        lambda subject: f"token-for-{subject}",
    )

    token = instance.authenticate(
        email=user.email,
        password="correct-password",
    )

    assert token == f"token-for-{user.id}"
    repository.get_by_email.assert_called_once_with(user.email)


def test_authenticate_rejects_unknown_user(service):
    instance, repository = service
    repository.get_by_email.return_value = None

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        instance.authenticate(
            email="unknown@forgeai.local",
            password="some-password",
        )


def test_authenticate_rejects_incorrect_password(
    service,
    user,
    monkeypatch,
):
    instance, repository = service
    repository.get_by_email.return_value = user

    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda password, hashed: False,
    )

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        instance.authenticate(
            email=user.email,
            password="wrong-password",
        )


def test_authenticate_rejects_inactive_user(
    service,
    user,
    monkeypatch,
):
    instance, repository = service
    user.is_active = False
    repository.get_by_email.return_value = user

    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda password, hashed: True,
    )

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        instance.authenticate(
            email=user.email,
            password="correct-password",
        )
