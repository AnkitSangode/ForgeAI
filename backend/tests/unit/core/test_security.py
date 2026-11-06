import pytest

from forgeai.core.security import hash_password, verify_password


def test_hash_password_returns_hash():
    password = "ForgeAI-Strong-Password-123!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert hashed_password.startswith("$argon2")


def test_same_password_generates_different_hashes():
    password = "ForgeAI-Strong-Password-123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_with_correct_password():
    password = "ForgeAI-Strong-Password-123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_verify_password_with_incorrect_password():
    hashed_password = hash_password("Correct-Password-123!")

    assert (
        verify_password(
            "Wrong-Password-123!",
            hashed_password,
        )
        is False
    )


def test_hash_password_rejects_empty_password():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")


@pytest.mark.parametrize(
    ("plain_password", "hashed_password"),
    [
        ("", "some-hash"),
        ("some-password", ""),
        ("", ""),
    ],
)
def test_verify_password_returns_false_for_empty_inputs(
    plain_password,
    hashed_password,
):
    assert verify_password(plain_password, hashed_password) is False
