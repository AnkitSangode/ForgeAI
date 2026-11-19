
from contextlib import contextmanager
from typing import Any, Iterator

from langfuse import Langfuse

from forgeai.core.config import Settings


class NoOpObservation:
    """Fallback observation when telemetry is unavailable."""

    def update(self, **kwargs: Any) -> None:
        return None


class LangfuseTelemetry:
    """Centralized, fail-open Langfuse integration."""

    def __init__(self, settings: Settings) -> None:
        self._client: Langfuse | None = None

        if not settings.langfuse_enabled:
            return

        if (
            settings.langfuse_public_key is None
            or settings.langfuse_secret_key is None
        ):
            raise ValueError(
                "Langfuse is enabled but its public or secret key is missing."
            )

        self._client = Langfuse(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            host=settings.langfuse_base_url,
        )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @contextmanager
    def generation(
        self,
        *,
        name: str,
        model: str,
        input_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[Any]:
        """Create a generation observation without exposing raw prompts."""

        if self._client is None:
            yield NoOpObservation()
            return

        try:
            observation_context = self._client.start_as_current_observation(
                as_type="generation",
                name=name,
                model=model,
                input=input_data,
                metadata=metadata or {},
            )
            observation = observation_context.__enter__()
        except Exception:
            # Telemetry initialization must not break an LLM request.
            yield NoOpObservation()
            return

        try:
            yield observation
        except BaseException as error:
            try:
                observation.update(
                    level="ERROR",
                    status_message=type(error).__name__,
                )
            except Exception:
                pass

            try:
                observation_context.__exit__(
                    type(error),
                    error,
                    error.__traceback__,
                )
            except Exception:
                pass

            raise
        else:
            try:
                observation_context.__exit__(None, None, None)
            except Exception:
                # Do not turn a successful LLM request into a failure.
                pass

    def flush(self) -> None:
        """Send buffered telemetry to Langfuse."""

        if self._client is not None:
            try:
                self._client.flush()
            except Exception:
                # Telemetry delivery must not crash application shutdown.
                pass

    @contextmanager
    def span(
        self,
        *,
        name: str,
        input_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[Any]:
        """Create a fail-open span for a non-LLM operation."""

        if self._client is None:
            yield NoOpObservation()
            return

        try:
            observation_context = self._client.start_as_current_observation(
                as_type="span",
                name=name,
                input=input_data,
                metadata=metadata or {},
            )
            observation = observation_context.__enter__()
        except Exception:
            yield NoOpObservation()
            return

        try:
            yield observation
        except BaseException as error:
            try:
                observation.update(
                    level="ERROR",
                    status_message=type(error).__name__,
                )
            except Exception:
                pass

            try:
                observation_context.__exit__(
                    type(error),
                    error,
                    error.__traceback__,
                )
            except Exception:
                pass

            raise
        else:
            try:
                observation_context.__exit__(None, None, None)
            except Exception:
                pass
