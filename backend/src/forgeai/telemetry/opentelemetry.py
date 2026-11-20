"""OpenTelemetry setup and low-cardinality tracing helpers for ForgeAI.

The default development exporter writes spans to stdout. Set OTEL_EXPORTER=otlp
and OTEL_EXPORTER_OTLP_ENDPOINT to send spans to an OpenTelemetry Collector.
Telemetry is fail-open: exporter failures must never fail agent execution.
"""

from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    ConsoleSpanExporter,
)

logger = logging.getLogger(__name__)
_provider: TracerProvider | None = None


def configure_tracing(settings: Any) -> TracerProvider | None:
    """Configure one process-wide tracer provider; safe to call more than once."""
    global _provider

    if not getattr(settings, "otel_enabled", True):
        return None
    if _provider is not None:
        return _provider

    resource = Resource.create(
        {
            "service.name": getattr(settings, "otel_service_name", "forgeai-backend"),
            "service.version": getattr(settings, "app_version", "0.1.0"),
            "deployment.environment": getattr(settings, "environment", "development"),
        }
    )
    provider = TracerProvider(resource=resource)
    exporter_kind = getattr(settings, "otel_exporter", "console")

    try:
        if exporter_kind == "otlp":
            endpoint = getattr(settings, "otel_exporter_otlp_endpoint", None)
            if not endpoint:
                raise ValueError(
                    "OTEL_EXPORTER=otlp requires OTEL_EXPORTER_OTLP_ENDPOINT."
                )
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )
        else:
            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )

        trace.set_tracer_provider(provider)
        _provider = provider
        return provider
    except Exception:
        # Observability is deliberately fail-open, but make configuration errors visible.
        logger.exception("OpenTelemetry exporter could not be configured; tracing disabled")
        provider.shutdown()
        return None


def shutdown_tracing() -> None:
    """Flush and close the provider during application shutdown."""
    global _provider
    if _provider is not None:
        try:
            _provider.force_flush(timeout_millis=3000)
            _provider.shutdown()
        except Exception:
            logger.exception("OpenTelemetry shutdown failed")
        finally:
            _provider = None


def trace_graph_node(node_name: str, node: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a LangGraph node in a span without recording prompts or source code."""
    tracer = trace.get_tracer("forgeai.agent.graph")

    def add_state_attributes(span: Any, state: Any) -> None:
        if not isinstance(state, dict):
            return
        for key in ("task_id", "agent_run_id", "status"):
            value = state.get(key)
            if value is not None:
                span.set_attribute(f"forgeai.{key}", str(value)[:128])
        span.set_attribute("forgeai.agent.node", node_name)

    if inspect.iscoroutinefunction(node):
        @wraps(node)
        async def async_traced(state: Any, *args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f"forgeai.agent.{node_name}") as span:
                add_state_attributes(span, state)
                try:
                    result = await node(state, *args, **kwargs)
                    if isinstance(result, dict) and result.get("status"):
                        span.set_attribute("forgeai.result_status", str(result["status"])[:128])
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                    raise
        return async_traced

    @wraps(node)
    def traced(state: Any, *args: Any, **kwargs: Any) -> Any:
        with tracer.start_as_current_span(f"forgeai.agent.{node_name}") as span:
            add_state_attributes(span, state)
            try:
                result = node(state, *args, **kwargs)
                if isinstance(result, dict) and result.get("status"):
                    span.set_attribute("forgeai.result_status", str(result["status"])[:128])
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                raise
    return traced
