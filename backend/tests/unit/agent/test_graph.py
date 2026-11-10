
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from forgeai.agent.graph import build_agent_graph
from forgeai.agent.schemas import PlanResponse, PlanStep
from forgeai.agent.researcher_schema import (
    ResearchFinding,
    ResearchResponse,
)
from forgeai.agent.coder_schema import CodeChange, CoderResponse
from forgeai.agent.reviewer_schema import ReviewResponse
from forgeai.execution.sandbox.base import (
    CommandExecutionResult,
    SandboxFileResult,
    SandboxSession,
)


@pytest.mark.unit
def test_graph_executes_successful_workflow():
    # ---------------------------------------------------------
    # Arrange: Sandbox session and provider
    # ---------------------------------------------------------

    sandbox_session = SandboxSession(
        sandbox_id="test-sandbox",
        _handle=MagicMock(),
    )

    sandbox_provider = MagicMock()

    sandbox_provider.create.return_value = sandbox_session
    sandbox_provider.file_exists.return_value = False
    sandbox_provider.is_running.return_value = True
    sandbox_provider.connect.return_value = sandbox_session

    # ---------------------------------------------------------
    # Arrange: Repository files
    # ---------------------------------------------------------

    file_contents = {
        "repository/pyproject.toml": """
[project]
name = "sample-project"
version = "0.1.0"
""",
        "repository/README.md": """
# Sample Project

A sample repository for testing ForgeAI.
""",
        "repository/src/auth.py": """
def authenticate(username: str, password: str) -> bool:
    return username == "admin" and password == "password"
""",
        "repository/tests/test_auth.py": """
def test_authenticate():
    assert True
""",
    }

    def mock_read_file(session, file_path):
        content = file_contents[file_path]

        return SandboxFileResult(
            file_path=file_path,
            content=content,
            sha256=sha256(content.encode("utf-8")).hexdigest(),
        )

    sandbox_provider.read_file.side_effect = mock_read_file

    # ---------------------------------------------------------
    # Arrange: Repository inspection results
    # ---------------------------------------------------------

    inspected_files = [
        "repository/pyproject.toml",
        "repository/README.md",
        "repository/src/auth.py",
        "repository/tests/test_auth.py",
    ]

    inspection_output = "\0".join(inspected_files) + "\0"

    command_results = [
        # Clone repository
        CommandExecutionResult(
            command="git clone",
            exit_code=0,
            stdout="",
            stderr="",
        ),

        # Resolve repository commit
        CommandExecutionResult(
            command="git rev-parse HEAD",
            exit_code=0,
            stdout="abc123def456\n",
            stderr="",
        ),

        # Inspect repository files
        CommandExecutionResult(
            command="find repository",
            exit_code=0,
            stdout=inspection_output,
            stderr="",
        ),
    ]

    # Each context file requires a type check and size check.
    for file_path in inspected_files:
        content = file_contents[file_path]
        size = len(content.encode("utf-8"))

        command_results.extend(
            [
                CommandExecutionResult(
                    command="file type check",
                    exit_code=0,
                    stdout="file",
                    stderr="",
                ),
                CommandExecutionResult(
                    command="file size check",
                    exit_code=0,
                    stdout=f"{size}\n",
                    stderr="",
                ),
            ]
        )

    sandbox_provider.run_command.side_effect = command_results

    # ---------------------------------------------------------
    # Arrange: Planner response
    # ---------------------------------------------------------

    planner_response = PlanResponse(
        objective="Identify and analyze authentication issues.",
        steps=[
            PlanStep(
                step_number=1,
                title="Inspect authentication implementation",
                description=(
                    "Review the authentication function and identify "
                    "potential weaknesses in its implementation."
                ),
                expected_output="Authentication implementation analysis.",
            ),
            PlanStep(
                step_number=2,
                title="Review authentication tests",
                description=(
                    "Inspect existing tests and identify missing "
                    "authentication test coverage."
                ),
                expected_output="Authentication test coverage assessment.",
            ),
        ],
        success_criteria=[
            "Authentication implementation is analyzed.",
            "Potential security weaknesses are identified.",
        ],
    )

    planner_agent = MagicMock()
    planner_agent.generate_plan.return_value = planner_response

    # ---------------------------------------------------------
    # Arrange: Researcher response
    # ---------------------------------------------------------

    researcher_response = ResearchResponse(
        summary=(
            "Authentication currently uses direct credential "
            "comparison and has limited test coverage."
        ),
        findings=[
            ResearchFinding(
                file_path="src/auth.py",
                evidence=(
                    'return username == "admin" and '
                    'password == "password"'
                ),
                observation=(
                    "The authentication implementation uses "
                    "hardcoded credentials."
                ),
                relevance=(
                    "Hardcoded credentials create a security "
                    "risk for the authentication system."
                ),
            )
        ],
        files_inspected=[
            "src/auth.py",
            "tests/test_auth.py",
        ],
        root_cause_hypothesis=(
            "The authentication implementation uses hardcoded "
            "credentials instead of a secure credential mechanism."
        ),
        confidence="high",
        remaining_questions=[],
    )

    researcher_agent = MagicMock()
    researcher_agent.research.return_value = researcher_response

    # ---------------------------------------------------------
    # Arrange: Coder response
    # ---------------------------------------------------------

    coder_response = CoderResponse(
        summary=(
            "Proposed an authentication implementation improvement."
        ),
        changes=[
            CodeChange(
                file_path="src/auth.py",
                change_type="modify",
                unified_diff=(
                    "--- a/src/auth.py\n"
                    "+++ b/src/auth.py\n"
                    "@@ -1,2 +1,3 @@\n"
                    "-def authenticate(username, password):\n"
                    "-    return username == 'admin' and password == 'password'\n"
                    "+def authenticate(username, password):\n"
                    "+    if not username or not password:\n"
                    "+        return False\n"
                    "+    return verify_credentials(username, password)\n"
                ),
                explanation=(
                    "Replace direct hardcoded credential comparison "
                    "with a credential verification mechanism."
                ),
            )
        ],
        tests_to_run=[
            "tests/test_auth.py",
        ],
        risks=[
            "The credential verification function must be implemented "
            "by the application."
        ],
    )

    coder_agent = MagicMock()
    coder_agent.generate_changes.return_value = coder_response

    # ---------------------------------------------------------
    # Arrange: Reviewer response
    # ---------------------------------------------------------

    reviewer_response = ReviewResponse(
        decision="approved",
        summary=(
            "The proposed authentication change has passed "
            "the review criteria."
        ),
        findings=[],
        strengths=[
            "Handles empty credentials.",
            "Avoids direct hardcoded credential comparison.",
        ],
        tests_to_run=[
            "tests/test_auth.py",
        ],
    )

    reviewer_agent = MagicMock()
    reviewer_agent.review.return_value = reviewer_response

    # ---------------------------------------------------------
    # Arrange: Build graph with injected dependencies
    # ---------------------------------------------------------

    graph = build_agent_graph(
        planner_agent=planner_agent,
        researcher_agent=researcher_agent,
        coder_agent=coder_agent,
        reviewer_agent=reviewer_agent,
        sandbox_provider=sandbox_provider,
    )

    initial_state = {
        "task_id": "test-task-001",
        "task_description": (
            "Inspect this repository and identify potential "
            "authentication bugs."
        ),
        "repository_url": (
            "https://github.com/example/sample-project"
        ),
    }

    # ---------------------------------------------------------
    # Act: Execute the graph exactly once
    # ---------------------------------------------------------

    result = graph.invoke(initial_state)

    # ---------------------------------------------------------
    # Assert: Workflow execution
    # ---------------------------------------------------------

    assert result["status"] == "review_completed"
    assert result["error"] == ""

    # Repository metadata
    assert result["repository_status"] == "available"
    assert result["repository_name"] == "sample-project"
    assert result["repository_path"] == "repository"
    assert result["repository_commit_sha"] == "abc123def456"

    # Repository inspection
    assert result["repository_files"]
    assert len(result["repository_files"]) == 4
    assert result["repository_truncated"] is False

    # Repository context
    assert result["repository_context_status"] == "available"
    assert len(result["repository_context_files"]) == 4
    assert result["repository_context_bytes"] > 0

    # Agent outputs
    assert result["plan"]
    assert result["research"]
    assert result["code_changes"]

    assert result["review"]["decision"] == "approved"

    # Agent invocation verification
    planner_agent.generate_plan.assert_called_once()
    researcher_agent.research.assert_called_once()
    coder_agent.generate_changes.assert_called_once()
    reviewer_agent.review.assert_called_once()

    # Sandbox interaction verification
    sandbox_provider.create.assert_called_once()
    sandbox_provider.read_file.assert_called()
    sandbox_provider.run_command.assert_called()

    # Verify that the sandbox ID is persisted in graph state.
    assert result["sandbox_id"] == "test-sandbox"

    # Verify that repository nodes reconnect to the existing sandbox.
    sandbox_provider.connect.assert_called()
