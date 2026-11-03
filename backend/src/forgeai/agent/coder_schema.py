from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CodeChange(BaseModel):
    file_path: str = Field(min_length=1, max_length=500)
    change_type: Literal["create", "modify", "delete"]
    unified_diff: str = Field(min_length=1, max_length=100_000)
    explanation: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def validate_change(self):
        if not self.file_path.strip():
            raise ValueError("File path cannot be blank.")

        if not self.unified_diff.strip():
            raise ValueError("Unified diff cannot be blank.")

        if not self.explanation.strip():
            raise ValueError("Explanation cannot be blank.")

        return self


class CoderResponse(BaseModel):
    summary: str = Field(min_length=10, max_length=2000)
    changes: list[CodeChange] = Field(min_length=1, max_length=20)
    tests_to_run: list[str] = Field(default_factory=list, max_length=20)
    risks: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_response(self):
        file_paths = [change.file_path for change in self.changes]

        if len(file_paths) != len(set(file_paths)):
            raise ValueError("Each file can only have one proposed change.")

        if any(not test.strip() for test in self.tests_to_run):
            raise ValueError("Test paths cannot be blank.")

        if any(not risk.strip() for risk in self.risks):
            raise ValueError("Risks cannot be blank.")

        return self
