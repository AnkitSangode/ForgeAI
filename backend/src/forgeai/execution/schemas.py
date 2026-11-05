from pydantic import BaseModel, ConfigDict, Field


class FileSnapshot(BaseModel):
    """Trusted record of a repository file at a specific point in time."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
