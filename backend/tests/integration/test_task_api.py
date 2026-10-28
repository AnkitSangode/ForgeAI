from uuid import uuid4

from fastapi.testclient import TestClient

from forgeai.domain import Task


def test_create_task_persists_to_database(
    client: TestClient,
    db_session,
):
    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Fix failing tests",
            "description": "Investigate and fix the test suite.",
            "repository_url": "https://github.com/example/repo",
        },
    )

    assert response.status_code == 201

    body = response.json()
    task_id = body["id"]

    assert body["title"] == "Fix failing tests"
    assert body["status"] == "pending"

    task = db_session.get(Task, task_id)
    assert task is not None
    assert task.title == "Fix failing tests"
    assert task.id is not None


def test_get_task_returns_persisted_task(
    client: TestClient,
    db_session,
):
    task = Task(
        title="Inspect repository",
        description="Inspect the project structure.",
        repository_url="https://github.com/example/repo",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Diagnostic checks: does the test session see the saved task?
    assert task.id is not None
    persisted_task = db_session.get(Task, task.id)
    assert persisted_task is not None
    assert persisted_task.title == "Inspect repository"

    response = client.get(f"/api/v1/tasks/{task.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(task.id)
    assert response.json()["title"] == "Inspect repository"


def test_get_unknown_task_returns_404(client: TestClient):
    unknown_id = uuid4()

    response = client.get(f"/api/v1/tasks/{unknown_id}")

    assert response.status_code == 404


def test_create_task_rejects_invalid_payload(
    client: TestClient,
):
    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "",
            "description": "Invalid task",
            "repository_url": "not-a-valid-url",
        },
    )

    assert response.status_code == 422
