
from datetime import UTC, datetime, timedelta
from uuid import uuid4,UUID

import pytest
from sqlalchemy.orm import Session

from forgeai.domain.agent_run import AgentRun, AgentRunStatus
from forgeai.infrastructure.models import Task
from forgeai.infrastructure.models.agent_run import AgentRun as AgentRunModel
from forgeai.infrastructure.repositories.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)


@pytest.fixture
def task(db_session: Session) -> Task:
    task = Task(
        title="Fix authentication bug",
        description="Fix token validation in the authentication module.",
        repository_url="https://github.com/example/repository",
    )
    db_session.add(task)
    db_session.flush()
    return task


@pytest.fixture
def repository(db_session: Session) -> SQLAlchemyAgentRunRepository:
    return SQLAlchemyAgentRunRepository(db_session)


@pytest.fixture
def sample_run(task: Task) -> AgentRun:
    now = datetime.now(UTC)

    return AgentRun(
        id=str(uuid4()),
        task_id=str(task.id),
        thread_id=str(uuid4()),
        status=AgentRunStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


def test_create_agent_run_persists_record(
    db_session: Session,
    repository: SQLAlchemyAgentRunRepository,
    sample_run: AgentRun,
) -> None:
    created_run = repository.create(sample_run)
    db_session.commit()

    persisted = db_session.get(AgentRunModel, UUID(sample_run.id))

    assert created_run == sample_run
    assert persisted is not None
    assert persisted.task_id == UUID(sample_run.task_id)
    assert persisted.thread_id == sample_run.thread_id
    assert persisted.status == AgentRunStatus.PENDING.value


def test_get_by_id_returns_agent_run(
    db_session: Session,
    repository: SQLAlchemyAgentRunRepository,
    sample_run: AgentRun,
) -> None:
    repository.create(sample_run)
    db_session.commit()

    result = repository.get_by_id(__import__("uuid").UUID(sample_run.id))

    assert result is not None
    assert result.id == sample_run.id
    assert result.task_id == sample_run.task_id
    assert result.thread_id == sample_run.thread_id
    assert result.status == AgentRunStatus.PENDING


def test_get_by_id_returns_none_for_missing_run(
    repository: SQLAlchemyAgentRunRepository,
) -> None:
    result = repository.get_by_id(uuid4())

    assert result is None


def test_get_by_thread_id_returns_agent_run(
    db_session: Session,
    repository: SQLAlchemyAgentRunRepository,
    sample_run: AgentRun,
) -> None:
    repository.create(sample_run)
    db_session.commit()

    result = repository.get_by_thread_id(sample_run.thread_id)

    assert result is not None
    assert result.id == sample_run.id
    assert result.thread_id == sample_run.thread_id


def test_get_by_thread_id_returns_none_for_missing_thread(
    repository: SQLAlchemyAgentRunRepository,
) -> None:
    result = repository.get_by_thread_id(str(uuid4()))

    assert result is None


def test_update_agent_run_persists_status(
    db_session: Session,
    repository: SQLAlchemyAgentRunRepository,
    sample_run: AgentRun,
) -> None:
    repository.create(sample_run)
    db_session.commit()

    updated_run = AgentRun(
        id=sample_run.id,
        task_id=sample_run.task_id,
        thread_id=sample_run.thread_id,
        status=AgentRunStatus.RUNNING,
        created_at=sample_run.created_at,
        updated_at=sample_run.updated_at + timedelta(seconds=1),
    )

    repository.update(updated_run)
    db_session.commit()

    result = repository.get_by_id(__import__("uuid").UUID(sample_run.id))

    assert result is not None
    assert result.status == AgentRunStatus.RUNNING
    assert result.updated_at == updated_run.updated_at


def test_update_missing_agent_run_raises_error(
    repository: SQLAlchemyAgentRunRepository,
    sample_run: AgentRun,
) -> None:
    with pytest.raises(ValueError, match="Agent run does not exist"):
        repository.update(sample_run)
