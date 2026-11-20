
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForgeAI"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: str = ""

    database_url: str = (
        "postgresql+psycopg://forgeai:forgeai@localhost:5432/forgeai"
    )

    # LLM provider selection
    llm_provider: Literal["openai", "ollama"] = "ollama"

    # OpenAI configuration
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1"
    openai_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    openai_timeout: float = Field(default=60.0, gt=0)
    openai_max_retries: int = Field(default=2, ge=0)

    # Ollama configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    ollama_timeout: float = Field(default=120.0, gt=0)

    # E2B sandbox configuration
    e2b_api_key: SecretStr | None = None
    e2b_sandbox_timeout: int = Field(default=300, ge=60, le=3600)
    e2b_template: str | None = None
    e2b_workspace_root: str = "/workspace"

    # Authentication configuration
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    # MCP configuration
    mcp_enabled: bool = True

    # Filesystem MCP
    mcp_filesystem_root: str = r"D:\Internship projects\forgeai"

    # Database MCP - dedicated read-only credentials
    mcp_database_readonly_url: SecretStr | None = None

    # MCP execution limits
    mcp_max_tool_calls: int = Field(default=10, ge=1, le=50)
    mcp_max_rounds: int = Field(default=5, ge=1, le=10)
    mcp_tool_timeout: float = Field(default=30.0, gt=0, le=120)
    mcp_max_output_bytes: int = Field(
        default=1_000_000,
        ge=1024,
        le=10_000_000,
    )

    langfuse_enabled: bool = False
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    # GitHub integration
    github_token: SecretStr | None = None
    github_api_url: str = "https://api.github.com"

    # OpenTelemetry tracing. Console export is useful for local verification;
    # production deployments should point an OTLP exporter at a collector.
    otel_enabled: bool = True
    otel_service_name: str = "forgeai-backend"
    otel_exporter: Literal["console", "otlp"] = "console"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
