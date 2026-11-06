
from unittest.mock import Mock

import pytest

from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.reviewer import ReviewerAgent
from forgeai.agent.reviewer_schema import (
    ReviewFinding,
    ReviewResponse,
)
from forgeai.agent.schemas import PlanResponse, PlanStep
from forgeai.llm.exceptions import LLMResponseError
from forgeai.llm.llm_service import LLMService
from forgeai.llm.schemas import LLMResponse


@pytest.fixture
def llm_service() -> Mock:
    return Mock(spec=LLMService)


@pytest.fixture
def reviewer(llm_service: Mock) -> ReviewerAgent:
    return ReviewerAgent(llm_service=llm_service)


@pytest.fixture
def plan() -> PlanResponse:
    return PlanResponse(
        objective="Fix the authentication validation bug.",
        steps=[
            PlanStep(
                step_number=1,
                title="Inspect authentication validation",
                description="Inspect the existing validation implementation.",
                expected_output="Identify the faulty validation condition.",
            )
        ],
        success_criteria=[
            "Invalid credentials must be rejected correctly."
        ],
    )


@pytest.fixture
def research() -> ResearchResponse:
    return ResearchResponse(
        summary="The authentication validation condition is incorrect.",
        findings=[
            ResearchFinding(
                file_path="src/auth.py",
                evidence="The validation condition accepts invalid credentials.",
                observation="The condition does not reject an invalid token.",
                relevance="This causes the authentication bug reported by the user.",
            )
        ],
        files_inspected=["src/auth.py"],
        root_cause_hypothesis="The token validation condition is implemented incorrectly.",
        confidence="high",
        remaining_questions=[],
    )


@pytest.fixture
def code_changes() -> CoderResponse:
    return CoderResponse(
        summary="Corrected the authentication validation condition.",
        changes=[
            CodeChange(
                file_path="src/auth.py",
                change_type="modify",
                unified_diff=(
                    "--- a/src/auth.py\n"
                    "+++ b/src/auth.py\n"
                    "@@ -1 +1 @@\n"
                    "-if token:\n"
                    "+if token is not None:\n"
                ),
                explanation="Correctly checks whether a token exists.",
            )
        ],
        tests_to_run=["tests/test_auth.py"],
        risks=[],
    )


@pytest.fixture
def repository_context_files() -> list[dict[str, str]]:
    return [
        {
            "file_path": "src/auth.py",
            "content": "def validate_token(token):\n    return token is not None\n",
        }
    ]


def test_review_returns_structured_review(
    reviewer: ReviewerAgent,
    llm_service: Mock,
    plan: PlanResponse,
    research: ResearchResponse,
    code_changes: CoderResponse,
    repository_context_files: list[dict[str, str]],
) -> None:
    expected_review = ReviewResponse(
        decision="approved",
        summary="The proposed change addresses the identified validation issue.",
        findings=[],
        strengths=["The change is focused and addresses the reported issue."],
        tests_to_run=["tests/test_auth.py"],
    )

    llm_service.generate.return_value = LLMResponse(
        content=expected_review,
        model="gpt-4.1",
    )

    result = reviewer.review(
        task_description="Fix the authentication validation bug.",
        plan=plan,
        research=research,
        code_changes=code_changes,
        repository_context_files=repository_context_files,
    )

    assert result == expected_review

    llm_service.generate.assert_called_once()
    call_kwargs = llm_service.generate.call_args.kwargs

    assert call_kwargs["response_schema"] is ReviewResponse
    assert "USER TASK:" in call_kwargs["prompt"]
    assert "PROPOSED CODE CHANGES:" in call_kwargs["prompt"]


def test_review_rejects_empty_task_description(
    reviewer: ReviewerAgent,
    plan: PlanResponse,
    research: ResearchResponse,
    code_changes: CoderResponse,
    repository_context_files: list[dict[str, str]],
) -> None:
    with pytest.raises(ValueError, match="Task description"):
        reviewer.review(
            task_description=" ",
            plan=plan,
            research=research,
            code_changes=code_changes,
            repository_context_files=repository_context_files,
        )


def test_review_rejects_empty_repository_context(
    reviewer: ReviewerAgent,
    plan: PlanResponse,
    research: ResearchResponse,
    code_changes: CoderResponse,
) -> None:
    with pytest.raises(ValueError, match="Repository context"):
        reviewer.review(
            task_description="Fix authentication.",
            plan=plan,
            research=research,
            code_changes=code_changes,
            repository_context_files=[],
        )


def test_review_rejects_invalid_llm_response(
    reviewer: ReviewerAgent,
    llm_service: Mock,
    plan: PlanResponse,
    research: ResearchResponse,
    code_changes: CoderResponse,
    repository_context_files: list[dict[str, str]],
) -> None:
    llm_service.generate.return_value = LLMResponse(
        content={"decision": "approved"},
        model="gpt-4.1",
    )

    with pytest.raises(
        LLMResponseError,
        match="invalid structured response",
    ):
        reviewer.review(
            task_description="Fix authentication.",
            plan=plan,
            research=research,
            code_changes=code_changes,
            repository_context_files=repository_context_files,
        )


def test_review_rejects_finding_outside_changed_files(
    reviewer: ReviewerAgent,
    llm_service: Mock,
    plan: PlanResponse,
    research: ResearchResponse,
    code_changes: CoderResponse,
    repository_context_files: list[dict[str, str]],
) -> None:
    invalid_review = ReviewResponse(
        decision="changes_requested",
        summary="The proposed patch needs additional corrections.",
        findings=[
            ReviewFinding(
                severity="medium",
                file_path="src/unrelated.py",
                description="This file contains a possible correctness issue.",
                recommendation="Investigate the relevant implementation.",
            )
        ],
        strengths=[],
        tests_to_run=[],
    )

    llm_service.generate.return_value = LLMResponse(
        content=invalid_review,
        model="gpt-4.1",
    )

    with pytest.raises(
        LLMResponseError,
        match="outside the proposed changes",
    ):
        reviewer.review(
            task_description="Fix authentication.",
            plan=plan,
            research=research,
            code_changes=code_changes,
            repository_context_files=repository_context_files,
        )
