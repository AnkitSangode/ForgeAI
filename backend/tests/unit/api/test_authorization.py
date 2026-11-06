from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from forgeai.api.dependencies.authorization import require_reviewer
from forgeai.infrastructure.models.user import UserRole


@pytest.mark.parametrize(
    "role",
    [UserRole.REVIEWER, UserRole.ADMIN],
)
def test_reviewer_and_admin_are_authorized(role):
    user = SimpleNamespace(
        id=uuid4(),
        role=role,
        is_active=True,
    )

    result = require_reviewer(user)

    assert result is user


def test_regular_user_is_forbidden():
    user = SimpleNamespace(
        id=uuid4(),
        role=UserRole.USER,
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_reviewer(user)

    assert exc_info.value.status_code == 403