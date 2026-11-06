from unittest.mock import Mock

import pytest

from forgeai.agent.coder_schema import CodeChange
from forgeai.application.approved_patch_execution_service import (
    ApprovedPatchExecutionService,
)
from forgeai.application.patch_approval_service import (
    ApprovalConsumptionError,
)
from forgeai.execution.application_result import PatchApplicationResult
from forgeai.execution.sandbox.base import SandboxSession


@pytest.fixture
def changes():
    return [
        CodeChange(
            file_path="src/auth.py",
            change_type="modify",
            unified_diff="@@ -1 +1 @@\n-old\n+new\n",
            explanation="Update the authentication logic.",
        )
    ]


@pytest.fixture
def session():
    return Mock(spec=SandboxSession)


@pytest.fixture
def repository_context():
    return Mock()


@pytest.fixture
def approval_service():
    return Mock()


@pytest.fixture
def patch_application_service():
    return Mock()


@pytest.fixture
def patch_validator():
    validator = Mock()
    validator.validate.return_value = None
    return validator


@pytest.fixture
def execution_service(
    approval_service,
    patch_application_service,
    patch_validator,
):
    return ApprovedPatchExecutionService(
        approval_service=approval_service,
        patch_application_service=patch_application_service,
        patch_validator=patch_validator,
    )


def test_valid_approval_executes_patch(
    execution_service,
    approval_service,
    patch_application_service,
    changes,
    session,
    repository_context,
):
    expected_result = Mock(spec=PatchApplicationResult)
    patch_application_service.apply.return_value = expected_result

    result = execution_service.execute(
        approval_id="approval-123",
        task_id="task-123",
        session=session,
        changes=changes,
        allowed_paths={"src/auth.py"},
        repository_context=repository_context,
    )

    approval_service.consume_approval.assert_called_once()

    patch_application_service.apply.assert_called_once_with(
        session=session,
        changes=changes,
        allowed_paths={"src/auth.py"},
        repository_context=repository_context,
    )

    assert result is expected_result


def test_approval_consumption_failure_prevents_patch_application(
    execution_service,
    approval_service,
    patch_application_service,
    changes,
    session,
    repository_context,
):
    approval_service.consume_approval.side_effect = ApprovalConsumptionError(
        "Approval cannot authorize this execution."
    )

    with pytest.raises(ApprovalConsumptionError):
        execution_service.execute(
            approval_id="approval-123",
            task_id="task-123",
            session=session,
            changes=changes,
            allowed_paths={"src/auth.py"},
            repository_context=repository_context,
        )

    patch_application_service.apply.assert_not_called()


def test_patch_application_failure_propagates(
    execution_service,
    approval_service,
    patch_application_service,
    changes,
    session,
    repository_context,
):
    patch_application_service.apply.side_effect = RuntimeError("Sandbox execution failed.")

    with pytest.raises(RuntimeError, match="Sandbox execution failed"):
        execution_service.execute(
            approval_id="approval-123",
            task_id="task-123",
            session=session,
            changes=changes,
            allowed_paths={"src/auth.py"},
            repository_context=repository_context,
        )

    approval_service.consume_approval.assert_called_once()
    patch_application_service.apply.assert_called_once()


def test_patch_validation_happens_before_approval_consumption(
    execution_service,
    approval_service,
    patch_application_service,
    patch_validator,
    changes,
    session,
    repository_context,
):
    patch_validator.validate.side_effect = ValueError("Invalid patch.")

    with pytest.raises(ValueError, match="Invalid patch"):
        execution_service.execute(
            approval_id="approval-123",
            task_id="task-123",
            session=session,
            changes=changes,
            allowed_paths={"src/auth.py"},
            repository_context=repository_context,
        )

    approval_service.consume_approval.assert_not_called()
    patch_application_service.apply.assert_not_called()


def test_approval_is_consumed_before_patch_application(
    execution_service,
    approval_service,
    patch_application_service,
    changes,
    session,
    repository_context,
):
    execution_order = []

    approval_service.consume_approval.side_effect = lambda **kwargs: execution_order.append(
        "approval_consumed"
    )
    patch_application_service.apply.side_effect = lambda **kwargs: execution_order.append(
        "patch_applied"
    )

    execution_service.execute(
        approval_id="approval-123",
        task_id="task-123",
        session=session,
        changes=changes,
        allowed_paths={"src/auth.py"},
        repository_context=repository_context,
    )

    assert execution_order == [
        "approval_consumed",
        "patch_applied",
    ]
