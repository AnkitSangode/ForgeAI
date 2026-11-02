from forgeai.agent.graph import agent_graph


def test_agent_graph_successfully_inspects_repository(tmp_path):
    # Arrange
    repository = tmp_path / "test-project"
    repository.mkdir()

    (repository / "README.md").write_text("# Test Project")
    (repository / "main.py").write_text("print('Hello')")

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    # Act
    result = agent_graph.invoke(initial_state)

    # Assert
    assert result["status"] == "plan_created"
    assert result["repository_status"] == "available"
    assert result["repository_files"]
    assert result["repository_truncated"] is False
    assert result["plan"]
    assert "README.md" in result["repository_files"]


def test_agent_graph_fails_when_repository_path_is_missing():
    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": "",
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["error"] == "Local repository path cannot be empty."
    assert "plan" not in result


def test_agent_graph_fails_when_repository_does_not_exist(tmp_path):
    repository = tmp_path / "nonexistent"

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["status"] == "failed"
    assert result["repository_status"] == "unavailable"
    assert result["repository_files"] == []
    assert result["error"] == "Repository path does not exist."
    assert "plan" not in result


def test_agent_graph_preserves_repository_truncation_status(tmp_path):
    repository = tmp_path / "test-project"
    repository.mkdir()

    (repository / "README.md").write_text("# Test Project")

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["repository_truncated"] is False


def test_agent_graph_continues_with_partial_repository_context(tmp_path):
    repository = tmp_path / "test-project"
    repository.mkdir()

    oversized_content = "x" * (100 * 1024 + 1)

    (repository / "README.md").write_text(
        oversized_content,
        encoding="utf-8",
    )

    (repository / "main.py").write_text(
        "def main(): pass",
        encoding="utf-8",
    )

    initial_state = {
        "task_id": "task-123",
        "task_description": "Fix authentication bug",
        "repository_url": "https://github.com/example/project",
        "repository_path": str(repository),
    }

    result = agent_graph.invoke(initial_state)

    assert result["repository_context_status"] == "partial"
    assert result["status"] == "plan_created"

    assert len(result["repository_context_files"]) == 1
    assert result["repository_context_files"][0]["file_path"] == "main.py"

    assert "README.md" in result["repository_context_skipped_files"]
    assert result["plan"]
