# OpenTelemetry tracing

ForgeAI emits traces for incoming HTTP requests and individual LangGraph nodes.
The graph spans include only bounded identifiers (`task_id`, `agent_run_id`),
node name, and returned status. Prompts, source files, authorization headers,
request bodies, and secrets are intentionally not recorded by this instrumentation.

## Local development (default)

OpenTelemetry is enabled by default and uses the console span exporter. Start the
API and inspect its terminal output for spans named `http.server.request` and
`forgeai.agent.<node-name>`.

```dotenv
OTEL_ENABLED=true
OTEL_EXPORTER=console
OTEL_SERVICE_NAME=forgeai-backend
```

## OTLP collector

For a local or hosted OpenTelemetry Collector, set the OTLP HTTP trace endpoint.
The endpoint should be the collector's `/v1/traces` URL.

```dotenv
OTEL_ENABLED=true
OTEL_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
OTEL_SERVICE_NAME=forgeai-backend
```

Install the updated project dependencies after applying this patch:

```powershell
uv sync
```

The tracing layer is fail-open: telemetry exporter/configuration failures are
logged and must not interrupt task execution. PostgreSQL-backed LangGraph
checkpointing remains the durable workflow state/history mechanism; OpenTelemetry
is for distributed traces, not a replacement for persisted application records.
