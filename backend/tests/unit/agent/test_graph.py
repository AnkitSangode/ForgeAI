from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from forgeai.agent.graph import build_agent_graph
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

    # ---------------------------------------------------------
    # Arrange: Repository files returned by the file reader
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
    # Arrange: Sandbox command responses
    #
    # 1. Git clone
    # 2. Resolve cloned repository commit
    # 3. Inspect repository files
    #
    # Each context file then requires:
    #   - One command to check file type
    #   - One command to check file size
    # ---------------------------------------------------------

    inspected_files = [
        "repository/pyproject.toml",
        "repository/README.md",
        "repository/src/auth.py",
        "repository/tests/test_auth.py",
    ]

    inspection_output = "\0".join(inspected_files) + "\0"

    command_results = [
        # 1. Clone repository
        CommandExecutionResult(
            command="git clone",
            exit_code=0,
            stdout="",
            stderr="",
        ),

        # 2. Get repository commit SHA
        CommandExecutionResult(
            command="git rev-parse HEAD",
            exit_code=0,
            stdout="abc123def456\n",
            stderr="",
        ),

        # 3. Inspect repository files
        CommandExecutionResult(
            command="find repository",
            exit_code=0,
            stdout=inspection_output,
            stderr="",
        ),
    ]

    # Add file-type and file-size responses for each file.
    for file_path in inspected_files:
        content = file_contents[file_path]
        size = len(content.encode("utf-8"))

        # File type check
        command_results.append(
            CommandExecutionResult(
                command="file type check",
                exit_code=0,
                stdout="file",
                stderr="",
            )
        )

        # File size check
        command_results.append(
            CommandExecutionResult(
                command="file size check",
                exit_code=0,
                stdout=f"{size}\n",
                stderr="",
            )
        )

    sandbox_provider.run_command.side_effect = command_results

    # ---------------------------------------------------------
    # Arrange: Agent graph
    # ---------------------------------------------------------

    graph = build_agent_graph(
        sandbox_provider=sandbox_provider,
    )

    initial_state = {
        "task_id": "test-task-001",
        "task_description": (
            "Inspect this repository and identify potential "
            "authentication bugs."
        ),
        "repository_url": "https://github.com/example/sample-project",
    }

    # ---------------------------------------------------------
    # Act: Execute the graph exactly once
    # ---------------------------------------------------------

    result = graph.invoke(initial_state)

    # ---------------------------------------------------------
    # Assert: Workflow execution
    # ---------------------------------------------------------

    assert result["status"] == "review_completed"

    # Repository metadata
    assert result["repository_status"] == "available"
    assert result["repository_name"] == "sample-project"
    assert result["repository_path"] == "repository"
    assert result["repository_commit_sha"] == "abc123def456"

    # Repository inspection
    assert result["repository_files"]
    assert len(result["repository_files"]) == 4

    # Repository context
    assert result["repository_context_status"] == "available"
    assert result["repository_context_files"]
    assert len(result["repository_context_files"]) == 4
    assert result["repository_context_bytes"] > 0

    # Agent execution
    assert result["plan"]
    assert result["research"]
    assert result["code_changes"]

    # Reviewer result
    assert result["review"]["decision"] == "approved"

    # Sandbox interactions
    sandbox_provider.create.assert_called_once()
    sandbox_provider.read_file.assert_called()
    sandbox_provider.run_command.assert_called()