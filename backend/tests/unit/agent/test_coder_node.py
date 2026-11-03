from unittest.mock import Mock

from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.agent.nodes import create_coder_node


def test_coder_node_stores_generated_changes():
    coder_agent = Mock()

    expected_response = CoderResponse(
        summary="Fix authentication validation.",
        changes=[
            CodeChange(
                file_path="src/auth.py",
                change_type="modify",
                unified_diff="@@ -1 +1 @@\n-old\n+new",
                explanation="Correct token expiration validation.",
            )
        ],
    )

    coder_agent.generate_changes.return_value = expected_response

    coder_node = create_coder_node(coder_agent)

    state = {
        "task_id": "task-123",
        "task_description": "Fix authentication validation.",
        "repository_url": "https://github.com/example/repo",
        "plan": {
            "objective": "Fix authentication validation.",
            "steps": [
                {
                    "step_number": 1,
                    "title": "Inspect authentication",
                    "description": "Inspect token expiration validation.",
                    "expected_output": "Identify the incorrect condition.",
                }
            ],
            "success_criteria": ["Expired tokens are rejected."],
        },
        "research": {
            "summary": "Found an incorrect expiration condition.",
            "findings": [
                {
                    "file_path": "src/auth.py",
                    "evidence": "if token.expired: return True",
                    "observation": "The expiration condition is incorrect.",
                    "relevance": "This may allow expired tokens.",
                }
            ],
            "files_inspected": ["src/auth.py"],
            "root_cause_hypothesis": "The expiration condition is reversed.",
            "confidence": "high",
            "remaining_questions": [],
        },
        "repository_context_files": [
            {
                "file_path": "src/auth.py",
                "content": "if token.expired: return True",
            }
        ],
        "status": "research_completed",
    }

    result = coder_node(state)

    assert result["status"] == "code_changes_generated"
    assert result["code_changes"] == expected_response.model_dump(mode="json")
    assert result["error"] == ""

    coder_agent.generate_changes.assert_called_once()


def test_coder_node_skips_when_workflow_has_failed():
    coder_agent = Mock()
    coder_node = create_coder_node(coder_agent)

    result = coder_node({"status": "failed", "error": "Research failed."})

    assert result == {}
    coder_agent.generate_changes.assert_not_called()


def test_coder_node_fails_when_plan_is_missing():
    coder_agent = Mock()
    coder_node = create_coder_node(coder_agent)

    result = coder_node(
        {
            "task_id": "task-123",
            "task_description": "Fix authentication.",
            "repository_url": "https://github.com/example/repo",
            "status": "research_completed",
        }
    )

    assert result["status"] == "failed"
    assert "no plan is available" in result["error"]
    coder_agent.generate_changes.assert_not_called()


def test_coder_node_fails_when_research_is_missing():
    coder_agent = Mock()
    coder_node = create_coder_node(coder_agent)

    result = coder_node(
        {
            "task_id": "task-123",
            "task_description": "Fix authentication.",
            "repository_url": "https://github.com/example/repo",
            "plan": {
                "objective": "Fix authentication validation.",
                "steps": [
                    {
                        "step_number": 1,
                        "title": "Inspect authentication",
                        "description": "Inspect token expiration validation.",
                        "expected_output": "Identify the incorrect condition.",
                    }
                ],
                "success_criteria": ["Expired tokens are rejected."],
            },
            "status": "plan_created",
        }
    )

    assert result["status"] == "failed"
    assert "no research is available" in result["error"]
    coder_agent.generate_changes.assert_not_called()


def test_coder_node_fails_when_repository_context_is_missing():
    coder_agent = Mock()
    coder_node = create_coder_node(coder_agent)

    result = coder_node(
        {
            "task_id": "task-123",
            "task_description": "Fix authentication.",
            "repository_url": "https://github.com/example/repo",
            "plan": {
                "objective": "Fix authentication validation.",
                "steps": [
                    {
                        "step_number": 1,
                        "title": "Inspect authentication",
                        "description": "Inspect token expiration validation.",
                        "expected_output": "Identify the incorrect condition.",
                    }
                ],
                "success_criteria": ["Expired tokens are rejected."],
            },
            "research": {
                "summary": "Found an incorrect expiration condition.",
                "findings": [
                    {
                        "file_path": "src/auth.py",
                        "evidence": "if token.expired: return True",
                        "observation": "The expiration condition is incorrect.",
                        "relevance": "This may allow expired tokens.",
                    }
                ],
                "files_inspected": ["src/auth.py"],
                "root_cause_hypothesis": "The expiration condition is reversed.",
                "confidence": "high",
                "remaining_questions": [],
            },
            "repository_context_files": [],
            "status": "research_completed",
        }
    )

    assert result["status"] == "failed"
    assert "repository context is unavailable" in result["error"]
    coder_agent.generate_changes.assert_not_called()


def test_coder_node_fails_when_plan_is_invalid():
    coder_agent = Mock()
    coder_node = create_coder_node(coder_agent)

    result = coder_node(
        {
            "task_id": "task-123",
            "task_description": "Fix authentication.",
            "repository_url": "https://github.com/example/repo",
            "plan": {"objective": "Invalid plan"},
            "research": {"summary": "Research data"},
            "repository_context_files": [
                {"file_path": "src/auth.py", "content": "authentication code"}
            ],
            "status": "research_completed",
        }
    )

    assert result["status"] == "failed"
    assert result["error"]
    coder_agent.generate_changes.assert_not_called()
