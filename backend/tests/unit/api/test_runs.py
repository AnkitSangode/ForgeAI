
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forgeai.api.runs import router
from forgeai.application.agent_run_service import AgentRunService
from forgeai.application.task_service import TaskNotFoundError, TaskService
from forgeai.domain.agent_run import AgentRun, AgentRunStatus
from forgeai.infrastructure.session import get_db


@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(router)
    application.state.graph = MagicMock()

    return application


@pytest.fixture
def client(app):
    app.dependency_overrides[get_db] = lambda: object()

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def sample_task():
    return SimpleNamespace(
        id=uuid4(),
        title="Fix authentication bug",
        description="Fix token validation.",
        repository_url="https://github.com/example/repo",
    )


@pytest.fixture
def sample_run(sample_task):
    now = datetime.now(UTC)

    return AgentRun(
        id=str(uuid4()),
        task_id=str(sample_task.id),
        thread_id=str(uuid4()),
        status=AgentRunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_run_service(sample_run, monkeypatch):
    service = MagicMock(spec=AgentRunService)

    service.create_run.return_value = sample_run

    def update_status(run_id, new_status):
        from dataclasses import replace

        return replace(
            sample_run,
            status=new_status,
            updated_at=datetime.now(UTC),
        )

    service.update_status.side_effect = update_status

    monkeypatch.setattr(
        "forgeai.api.runs.AgentRunService",
        lambda session: service,
    )

    monkeypatch.setattr(
        "forgeai.api.runs.SessionLocal",
        lambda: MagicMock(),
    )

    return service


def test_start_agent_run_success(
    app,
    client,
    sample_task,
    sample_run,
    mock_run_service,
    monkeypatch,
):
    monkeypatch.setattr(
        TaskService,
        "get_task",
        lambda self, task_id: sample_task,
    )

    app.state.graph.invoke.return_value = {
        "status": "completed",
        "review": {"decision": "approved"},
    }

    response = client.post(
        f"/api/v1/tasks/{sample_task.id}/runs"
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == sample_run.id
    assert body["task_id"] == str(sample_task.id)
    assert body["thread_id"] == sample_run.thread_id
    assert body["status"] == "awaiting_approval"

    mock_run_service.create_run.assert_called_once_with(
        str(sample_task.id)
    )

    app.state.graph.invoke.assert_called_once()

    _, kwargs = app.state.graph.invoke.call_args

    assert kwargs["config"]["configurable"]["thread_id"] == (
        sample_run.thread_id
    )


def test_start_agent_run_rejected(
    app,
    client,
    sample_task,
    mock_run_service,
    monkeypatch,
):
    monkeypatch.setattr(
        TaskService,
        "get_task",
        lambda self, task_id: sample_task,
    )

    app.state.graph.invoke.return_value = {
        "status": "completed",
        "review": {"decision": "rejected"},
    }

    response = client.post(
        f"/api/v1/tasks/{sample_task.id}/runs"
    )

    assert response.status_code == 201
    assert response.json()["status"] == "rejected"


def test_start_agent_run_graph_failure(
    app,
    client,
    sample_task,
    mock_run_service,
    monkeypatch,
):
    monkeypatch.setattr(
        TaskService,
        "get_task",
        lambda self, task_id: sample_task,
    )

    app.state.graph.invoke.return_value = {
        "status": "failed",
        "error": "Repository cloning failed",
    }

    response = client.post(
        f"/api/v1/tasks/{sample_task.id}/runs"
    )

    assert response.status_code == 201
    assert response.json()["status"] == "failed"

    assert any(
        call.args[1] == AgentRunStatus.FAILED
        for call in mock_run_service.update_status.call_args_list
    )


def test_start_agent_run_task_not_found(
    client,
    sample_run,
    monkeypatch,
):
    def fake_get_task(self, task_id):
        raise TaskNotFoundError("Task not found")

    monkeypatch.setattr(TaskService, "get_task", fake_get_task)

    response = client.post(
        f"/api/v1/tasks/{sample_run.task_id}/runs"
    )

    assert response.status_code == 404


def test_start_agent_run_graph_unavailable(
    app,
    client,
    sample_task,
    monkeypatch,
):
    monkeypatch.setattr(
        TaskService,
        "get_task",
        lambda self, task_id: sample_task,
    )

    app.state.graph = None

    response = client.post(
        f"/api/v1/tasks/{sample_task.id}/runs"
    )

    assert response.status_code == 503


def test_start_agent_run_graph_exception(
    app,
    client,
    sample_task,
    mock_run_service,
    monkeypatch,
):
    monkeypatch.setattr(
        TaskService,
        "get_task",
        lambda self, task_id: sample_task,
    )

    app.state.graph.invoke.side_effect = RuntimeError(
        "Unexpected graph failure"
    )

    response = client.post(
        f"/api/v1/tasks/{sample_task.id}/runs"
    )

    assert response.status_code == 500

    assert any(
        call.args[1] == AgentRunStatus.FAILED
        for call in mock_run_service.update_status.call_args_list
    )


def test_start_agent_run_invalid_task_uuid(client):
    response = client.post(
        "/api/v1/tasks/not-a-uuid/runs"
    )

    assert response.status_code == 422
