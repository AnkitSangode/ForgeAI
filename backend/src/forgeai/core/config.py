from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForgeAI"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://forgeai:forgeai@localhost:5432/forgeai"

    # OpenAI configuration
    openai_api_key: SecretStr
    openai_model: str = "gpt-4.1"
    openai_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    openai_timeout: float = Field(default=60.0, gt=0)
    openai_max_retries: int = Field(default=2, ge=0)

    # E2B sandbox configuration
    e2b_api_key: SecretStr | None = None
    e2b_sandbox_timeout: int = Field(default=300, ge=60, le=3600)
    e2b_template: str | None = None
    e2b_workspace_root: str = "/workspace"

    # Authentication configuration
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
