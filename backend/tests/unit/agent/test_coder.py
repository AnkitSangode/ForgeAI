from unittest.mock import Mock

import pytest

from forgeai.agent.coder import CoderAgent
from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.schemas import PlanResponse, PlanStep
from forgeai.llm.exceptions import LLMResponseError
from forgeai.llm.schemas import LLMResponse


def test_coder_generates_valid_code_changes():
    llm_service = Mock()

    expected_response = CoderResponse(
        summary="Fix authentication token expiration validation.",
        changes=[
            CodeChange(
                file_path="src/auth.py",
                change_type="modify",
                unified_diff="@@ -1 +1 @@\n-old\n+new",
                explanation="Correct token expiration validation.",
            )
        ],
        tests_to_run=["tests/test_auth.py"],
        risks=["Existing authentication behavior may change."],
    )

    llm_service.generate.return_value = LLMResponse(
        content=expected_response,
        model="test-model",
    )

    coder = CoderAgent(llm_service=llm_service)

    plan = PlanResponse(
        objective="Fix the authentication bug.",
        steps=[
            PlanStep(
                step_number=1,
                title="Inspect authentication",
                description="Inspect token expiration validation.",
                expected_output="Identify the incorrect validation.",
            )
        ],
        success_criteria=["Expired tokens are rejected."],
    )

    research = ResearchResponse(
        summary="Token expiration validation is incorrect.",
        findings=[
            ResearchFinding(
                file_path="src/auth.py",
                evidence="if token.expired: return True",
                observation="The expiration condition is incorrect.",
                relevance="This may allow expired tokens.",
            )
        ],
        files_inspected=["src/auth.py"],
        root_cause_hypothesis="The expiration condition is reversed.",
        confidence="high",
    )

    result = coder.generate_changes(
        task_description="Fix the authentication bug.",
        plan=plan,
        research=research,
        repository_context_files=[
            {
                "file_path": "src/auth.py",
                "content": "if token.expired: return True",
            }
        ],
    )

    assert result == expected_response
    llm_service.generate.assert_called_once()


def test_coder_rejects_empty_task():
    coder = CoderAgent(llm_service=Mock())

    with pytest.raises(ValueError, match="Task description cannot be empty"):
        coder.generate_changes(
            task_description="   ",
            plan=Mock(),
            research=Mock(findings=[Mock()]),
            repository_context_files=[{"file_path": "src/auth.py", "content": "pass"}],
        )


def test_coder_rejects_empty_repository_context():
    coder = CoderAgent(llm_service=Mock())

    with pytest.raises(ValueError, match="Repository context cannot be empty"):
        coder.generate_changes(
            task_description="Fix authentication.",
            plan=Mock(),
            research=Mock(findings=[Mock()]),
            repository_context_files=[],
        )


def test_coder_rejects_duplicate_repository_paths():
    coder = CoderAgent(llm_service=Mock())

    with pytest.raises(ValueError, match="Duplicate repository file paths"):
        coder.generate_changes(
            task_description="Fix authentication.",
            plan=Mock(),
            research=Mock(findings=[Mock()]),
            repository_context_files=[
                {"file_path": "src/auth.py", "content": "code"},
                {"file_path": "src/auth.py", "content": "different code"},
            ],
        )


def test_coder_rejects_unavailable_existing_file():
    llm_service = Mock()

    llm_service.generate.return_value = LLMResponse(
        content=CoderResponse(
            summary="Modify authentication validation.",
            changes=[
                CodeChange(
                    file_path="src/nonexistent.py",
                    change_type="modify",
                    unified_diff="@@ -1 +1 @@\n-old\n+new",
                    explanation="Modify authentication validation.",
                )
            ],
        ),
        model="test-model",
    )

    coder = CoderAgent(llm_service=llm_service)

    with pytest.raises(
        LLMResponseError,
        match="unavailable existing file",
    ):
        coder.generate_changes(
            task_description="Fix authentication.",
            plan=Mock(),
            research=Mock(findings=[Mock()]),
            repository_context_files=[
                {"file_path": "src/auth.py", "content": "authentication code"}
            ],
        )
