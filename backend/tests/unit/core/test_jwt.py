from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr

from forgeai.core import security


@pytest.fixture
def test_settings(monkeypatch):
    class FakeSettings:
        jwt_secret_key = SecretStr("test-secret-key-that-is-long-enough")
        jwt_algorithm = "HS256"
        access_token_expire_minutes = 30

    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: FakeSettings(),
    )


def test_create_access_token_returns_token(test_settings):
    user_id = str(uuid4())

    token = security.create_access_token(user_id)

    assert isinstance(token, str)
    assert len(token.split(".")) == 3


def test_decode_access_token_returns_expected_claims(test_settings):
    user_id = str(uuid4())

    token = security.create_access_token(user_id)
    payload = security.decode_access_token(token)

    assert payload["sub"] == user_id
    assert "iat" in payload
    assert "exp" in payload


def test_expired_token_is_rejected(test_settings):
    user_id = str(uuid4())

    token = security.create_access_token(
        user_id,
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token)


def test_token_signed_with_wrong_secret_is_rejected(test_settings):
    user_id = str(uuid4())

    token = security.create_access_token(user_id)

    class WrongSettings:
        jwt_secret_key = SecretStr("a-different-test-secret")
        jwt_algorithm = "HS256"
        access_token_expire_minutes = 30

    # Decode using a different signing secret.
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            token,
            WrongSettings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
        )


def test_malformed_token_is_rejected(test_settings):
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token("not-a-valid-jwt")


def test_empty_subject_is_rejected(test_settings):
    with pytest.raises(ValueError, match="Token subject cannot be empty"):
        security.create_access_token("")
