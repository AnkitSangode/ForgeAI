from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials submitted by a user."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Access token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """Public information about the authenticated user."""

    id: str
    email: EmailStr
    is_active: bool
