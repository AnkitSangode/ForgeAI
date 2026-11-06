
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReviewFinding(BaseModel):
    """One issue identified during patch review."""

    severity: Literal["critical", "high", "medium", "low"]
    file_path: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=10, max_length=1000)
    recommendation: str = Field(min_length=10, max_length=1000)


class ReviewResponse(BaseModel):
    """Structured review result for proposed code changes."""

    decision: Literal["approved", "changes_requested", "rejected"]

    summary: str = Field(min_length=10, max_length=2000)

    findings: list[ReviewFinding] = Field(
        default_factory=list,
        max_length=20,
    )

    strengths: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    tests_to_run: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    @model_validator(mode="after")
    def validate_review(self):
        if any(not item.strip() for item in self.strengths):
            raise ValueError("Strengths cannot contain empty values.")

        if any(not item.strip() for item in self.tests_to_run):
            raise ValueError("Test paths cannot be blank.")

        if self.decision == "approved":
            if any(
                finding.severity in {"critical", "high"}
                for finding in self.findings
            ):
                raise ValueError(
                    "A patch with critical or high severity findings "
                    "cannot be approved."
                )

        if self.decision == "rejected" and not self.findings:
            raise ValueError(
                "A rejected patch must include at least one finding."
            )

        return self
