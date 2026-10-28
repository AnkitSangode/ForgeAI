import pytest
from pydantic import ValidationError

from forgeai.api.schemas.task import TaskCreate


def test_task_create_accepts_valid_data():
    task = TaskCreate(
        title="fix failing tests",
        description="Investigate failing test",
        repository_url="https://github.com/example/repo",
    )

    assert task.title == "fix failing tests"
    assert str(task.repository_url).startswith("https://")


def test_task_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        TaskCreate(
            title="",
            description="Investigate failing test",
            repository_url="https://github.com/example/repo",
        )


def test_task_create_reject_invalid_url():
    
    with pytest.raises(ValidationError):
        TaskCreate(
            title="fix failing tests",
            description= "Investigate failing test",
            repository_url= "Invalid URL"
        )