import hashlib
from unittest.mock import MagicMock, patch

import pytest
from e2b import Sandbox

from forgeai.core.config import Settings
from forgeai.execution.sandbox.base import SandboxSession
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="test-key",
        e2b_api_key="test-e2b-key",
    )


@pytest.fixture
def provider(settings: Settings) -> E2BSandboxProvider:
    return E2BSandboxProvider(settings)


@pytest.fixture
def mock_sandbox() -> MagicMock:
    sandbox = MagicMock(spec=Sandbox)

    sandbox.sandbox_id = "test-sandbox-123"
    sandbox.is_running.return_value = True

    return sandbox


@pytest.fixture
def session(mock_sandbox: MagicMock) -> SandboxSession:
    return SandboxSession(
        sandbox_id="test-sandbox-123",
        _handle=mock_sandbox,
    )


def test_create_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = False

    result = provider.create_file(
        session,
        "src/example.py",
        "print('hello')",
    )

    assert result.file_path == "src/example.py"
    mock_sandbox.files.write.assert_called_once_with(
        "/workspace/src/example.py",
        "print('hello')",
    )


def test_create_file_rejects_existing_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = True

    with pytest.raises(FileExistsError):
        provider.create_file(
            session,
            "src/example.py",
            "new content",
        )

    mock_sandbox.files.write.assert_not_called()


def test_read_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.read.return_value = "print('hello')"

    result = provider.read_file(session, "src/example.py")

    assert result.content == "print('hello')"
    mock_sandbox.files.read.assert_called_once_with(
        "/workspace/src/example.py",
    )


def test_write_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = True

    result = provider.write_file(
        session,
        "src/example.py",
        "print('updated')",
    )

    assert result.file_path == "src/example.py"
    mock_sandbox.files.write.assert_called_once_with(
        "/workspace/src/example.py",
        "print('updated')",
    )


def test_write_file_rejects_missing_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = False

    with pytest.raises(FileNotFoundError):
        provider.write_file(
            session,
            "src/missing.py",
            "content",
        )

    mock_sandbox.files.write.assert_not_called()


def test_delete_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = True

    provider.delete_file(session, "src/example.py")

    mock_sandbox.files.remove.assert_called_once_with(
        "/workspace/src/example.py",
    )


def test_delete_file_rejects_missing_file(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = False

    with pytest.raises(FileNotFoundError):
        provider.delete_file(session, "src/missing.py")

    mock_sandbox.files.remove.assert_not_called()


@pytest.mark.parametrize(
    "invalid_path",
    [
        "../outside.py",
        "/etc/passwd",
        "src/../../outside.py",
        r"src\example.py",
    ],
)
def test_rejects_unsafe_paths(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    invalid_path: str,
) -> None:
    with pytest.raises(ValueError):
        provider.read_file(session, invalid_path)


def test_terminate(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    provider.terminate(session)

    mock_sandbox.kill.assert_called_once()


def test_file_exists_returns_true(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = True

    result = provider.file_exists(
        session,
        "src/auth.py",
    )

    assert result is True
    mock_sandbox.files.exists.assert_called_once_with(
        "/workspace/src/auth.py",
    )


def test_file_exists_returns_false(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    mock_sandbox.files.exists.return_value = False

    result = provider.file_exists(
        session,
        "src/auth.py",
    )

    assert result is False


def test_read_file_returns_content_and_sha256(
    provider: E2BSandboxProvider,
    session: SandboxSession,
    mock_sandbox: MagicMock,
) -> None:
    content = "def authenticate():\n    return True\n"
    mock_sandbox.files.read.return_value = content

    result = provider.read_file(
        session,
        "src/auth.py",
    )

    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert result.content == content
    assert result.sha256 == expected_hash
    assert result.file_path == "src/auth.py"


def test_connect_reconnects_to_existing_sandbox(
    provider: E2BSandboxProvider,
    mock_sandbox: MagicMock,
) -> None:
    with patch(
        "forgeai.execution.sandbox.e2b_provider.Sandbox._cls_connect_sandbox",
        return_value=mock_sandbox,
    ) as connect_mock:
        session = provider.connect("test-sandbox-123")

    connect_mock.assert_called_once_with(
        sandbox_id="test-sandbox-123",
        timeout=provider._timeout,
        on_resume="restore",
        api_key=provider._api_key,
    )

    assert session.sandbox_id == "test-sandbox-123"
    assert session._handle is mock_sandbox


def test_connect_rejects_empty_sandbox_id(
    provider: E2BSandboxProvider,
) -> None:
    with (
        patch(
            "forgeai.execution.sandbox.e2b_provider.Sandbox._cls_connect_sandbox",
        ) as connect_mock,
        pytest.raises(ValueError, match="Sandbox ID cannot be empty"),
    ):
        provider.connect("")

    connect_mock.assert_not_called()


def test_connect_propagates_sdk_errors(
    provider: E2BSandboxProvider,
) -> None:
    with (
        patch(
            "forgeai.execution.sandbox.e2b_provider.Sandbox._cls_connect_sandbox",
            side_effect=RuntimeError("Sandbox is unavailable"),
        ),
        pytest.raises(RuntimeError, match="Sandbox is unavailable"),
    ):
        provider.connect("test-sandbox-123")
