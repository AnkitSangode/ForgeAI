from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ResearchFinding(BaseModel):
    file_path: str = Field(min_length=1, max_length=500)
    evidence: str = Field(min_length=10, max_length=2000)
    observation: str = Field(min_length=10, max_length=1000)
    relevance: str = Field(min_length=10, max_length=1000)

    @model_validator(mode="after")
    def validate_non_blank_fields(self):
        fields = (
            self.file_path,
            self.evidence,
            self.observation,
            self.relevance,
        )

        if any(not value.strip() for value in fields):
            raise ValueError("Research finding fields cannot be blank.")

        return self


class ResearchResponse(BaseModel):
    summary: str = Field(min_length=10, max_length=2000)
    findings: list[ResearchFinding] = Field(min_length=1, max_length=20)
    files_inspected: list[str] = Field(min_length=1, max_length=20)
    root_cause_hypothesis: str = Field(min_length=10, max_length=2000)
    confidence: Literal["low", "medium", "high"]
    remaining_questions: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_research_output(self):
        if any(not path.strip() for path in self.files_inspected):
            raise ValueError("Inspected file paths cannot be blank.")

        if len(self.files_inspected) != len(set(self.files_inspected)):
            raise ValueError("Inspected file paths must be unique.")

        if any(not question.strip() for question in self.remaining_questions):
            raise ValueError("Remaining questions cannot contain blank values.")

        inspected_paths = set(self.files_inspected)

        for finding in self.findings:
            if finding.file_path not in inspected_paths:
                raise ValueError("Every finding must reference a file listed in files_inspected.")

        return self
