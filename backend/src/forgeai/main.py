
import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from sqlalchemy.engine import make_url

from forgeai.agent.coder import CoderAgent
from forgeai.agent.graph import build_agent_graph
from forgeai.agent.planner import PlannerAgent
from forgeai.agent.researcher import ResearcherAgent
from forgeai.agent.reviewer import ReviewerAgent

from forgeai.api.approvals import router as approvals_router
from forgeai.api.auth import router as auth_router
from forgeai.api.github import router as github_router
from forgeai.api.health import router as health_router
from forgeai.api.runs import router as runs_router
from forgeai.api.runs import runs_collection_router
from forgeai.api.tasks import router as tasks_router

from forgeai.application.approved_patch_execution_worker import (
    ApprovedPatchExecutionWorker,
)
from forgeai.application.github.github_service import GitHubService
from forgeai.application.mcp.mcp_connection_service import (
    MCPConnectionService,
)
from forgeai.application.mcp.mcp_research_service import MCPResearchService
from forgeai.application.mcp.mcp_tool_discovery_service import (
    MCPToolDiscoveryService,
)
from forgeai.application.mcp.mcp_tool_execution_service import (
    MCPToolExecutionService,
)
from forgeai.application.mcp.mcp_tool_policy import MCPToolPolicy
from forgeai.application.patch_preparation_service import (
    PatchPreparationService,
)

from forgeai.core.config import get_settings

from forgeai.execution.file_integrity_verifier import FileIntegrityVerifier
from forgeai.execution.git_change_verifier import GitChangeVerifier
from forgeai.execution.git_state_collector import GitStateCollector
from forgeai.execution.patch_application import PatchApplicationService
from forgeai.execution.patch_builder import PatchBuilder
from forgeai.execution.patch_validator import PatchValidator
from forgeai.execution.post_application_verifier import (
    PostApplicationVerifier,
)
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider

from forgeai.infrastructure.github.github_client import GitHubClient
from forgeai.infrastructure.mcp import MCPClientManager, MCPServerConfig
from forgeai.infrastructure.mcp.servers.playwright_server_config import (
    create_playwright_server_config,
)
from forgeai.infrastructure.session import SessionLocal

from forgeai.llm.llm_service import LLMService
from forgeai.llm.ollama_provider import OllamaProvider
from forgeai.llm.openai_provider import OpenAIProvider

from forgeai.services.repository_context_result import (
    RepositoryContextResult,
    RepositoryFileContext,
)

from forgeai.telemetry.langfuse_client import LangfuseTelemetry
from forgeai.telemetry.opentelemetry import configure_tracing, shutdown_tracing
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


settings = get_settings()
configure_tracing(settings)


def build_mcp_server_configs() -> list[MCPServerConfig]:
    """Build configurations for all trusted MCP servers."""

    # Preserve the parent process environment.
    # MCP subprocesses need access to PATH, Python and Node environments.
    process_env = dict(os.environ)

    if settings.mcp_database_readonly_url is None:
        raise RuntimeError(
            "MCP_DATABASE_READONLY_URL must be configured "
            "when MCP is enabled."
        )

    process_env["MCP_DATABASE_READONLY_URL"] = (
        settings.mcp_database_readonly_url.get_secret_value()
    )

    process_env["MCP_FILESYSTEM_ROOT"] = settings.mcp_filesystem_root

    python_servers = [
        MCPServerConfig(
            name="postgres",
            command=sys.executable,
            args=(
                "-m",
                "forgeai.infrastructure.mcp.servers.postgres_server",
            ),
            env=process_env,
        ),
        MCPServerConfig(
            name="filesystem",
            command=sys.executable,
            args=(
                "-m",
                "forgeai.infrastructure.mcp.servers.filesystem_server",
            ),
            env=process_env,
        ),
        MCPServerConfig(
            name="web_search",
            command=sys.executable,
            args=(
                "-m",
                "forgeai.infrastructure.mcp.servers.web_search_server",
            ),
            env=process_env,
        ),
    ]

    playwright_config = create_playwright_server_config()

    return [*python_servers, playwright_config]


def build_mcp_policy() -> MCPToolPolicy:
    """Define the MCP servers and tools ForgeAI is permitted to use."""

    return MCPToolPolicy(
        allowed_servers=frozenset(
            {
                "postgres",
                "filesystem",
                "web_search",
                "playwright",
            }
        ),
        allowed_tools={
            "postgres": frozenset(
                {
                    "list_tables",
                    "describe_table",
                    "read_records",
                }
            ),
            "filesystem": frozenset(
                {
                    "list_files",
                    "read_file",
                    "search_files",
                    "get_file_info",
                }
            ),
            "web_search": frozenset(
                {
                    "search_web",
                }
            ),
            "playwright": frozenset(
                {
                    "browser_navigate",
                    "browser_snapshot",
                }
            ),
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage long-lived application resources.

    Startup:
    - Initialize PostgreSQL checkpoint connection pool.
    - Initialize LangGraph PostgreSQL checkpointer.
    - Initialize Langfuse telemetry.
    - Construct shared LLM and agent dependencies.
    - Start trusted MCP servers when enabled.
    - Construct GitHub integration when configured.
    - Construct E2B sandbox provider.
    - Compile the agent graph.

    Shutdown:
    - Disconnect MCP servers.
    - Close the GitHub HTTP client.
    - Flush Langfuse telemetry.
    - Close the checkpoint connection pool.
    - Flush OpenTelemetry tracing.
    """

    if settings.e2b_api_key is None:
        raise RuntimeError(
            "E2B_API_KEY must be configured before starting ForgeAI."
        )

    conninfo = (
        make_url(settings.database_url)
        .set(drivername="postgresql")
        .render_as_string(hide_password=False)
    )

    checkpoint_pool = ConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        open=False,
    )

    mcp_connection_service = None
    mcp_client_manager = None
    telemetry = None
    github_client = None

    # GitHub is optional. The rest of ForgeAI can start without it.
    app.state.github_service = None

    try:
        # 1. Open PostgreSQL connection pool.
        checkpoint_pool.open(wait=True)

        # 2. Initialize LangGraph PostgreSQL checkpointer.
        checkpointer = PostgresSaver(checkpoint_pool)
        checkpointer.setup()

        # 3. Initialize the configured LLM provider.
        if settings.llm_provider == "ollama":
            llm_provider = OllamaProvider(settings)

        elif settings.llm_provider == "openai":
            llm_provider = OpenAIProvider(settings)

        else:
            raise ValueError(
                f"Unsupported LLM provider: {settings.llm_provider}"
            )

        # 4. Initialize Langfuse telemetry.
        # Telemetry is injected into the shared LLM service.
        telemetry = LangfuseTelemetry(settings)

        llm_service = LLMService(
            provider=llm_provider,
            telemetry=telemetry,
        )

        # 5. Initialize GitHub integration when configured.
        if settings.github_token is not None:
            github_client = GitHubClient(
                token=settings.github_token,
                base_url=settings.github_api_url,
            )

            app.state.github_service = GitHubService(
                client=github_client,
            )

        # 6. Initialize MCP infrastructure.
        mcp_research_service = None

        if settings.mcp_enabled:
            mcp_client_manager = MCPClientManager()

            mcp_policy = build_mcp_policy()

            mcp_connection_service = MCPConnectionService(
                client_manager=mcp_client_manager,
                policy=mcp_policy,
            )

            mcp_discovery_service = MCPToolDiscoveryService(
                client_manager=mcp_client_manager,
            )

            mcp_execution_service = MCPToolExecutionService(
                client_manager=mcp_client_manager,
                discovery_service=mcp_discovery_service,
                policy=mcp_policy,
                timeout_seconds=settings.mcp_tool_timeout,
                max_output_bytes=settings.mcp_max_output_bytes,
                telemetry=telemetry,
            )

            # Connect all configured MCP servers.
            server_configs = build_mcp_server_configs()

            for server_config in server_configs:
                await mcp_connection_service.connect(server_config)

            # Construct the MCP research coordinator.
            mcp_research_service = MCPResearchService(
                llm_service=llm_service,
                discovery_service=mcp_discovery_service,
                execution_service=mcp_execution_service,
                server_names=(
                    "postgres",
                    "filesystem",
                    "web_search",
                    "playwright",
                ),
                max_rounds=settings.mcp_max_rounds,
            )

        # 7. Construct agents using the shared LLM service.
        planner_agent = PlannerAgent(llm_service)
        researcher_agent = ResearcherAgent(llm_service)
        coder_agent = CoderAgent(llm_service)
        reviewer_agent = ReviewerAgent(llm_service)

        # 8. Construct E2B sandbox provider.
        sandbox_provider = E2BSandboxProvider(settings)

        # 9. Construct patch preparation dependencies.
        patch_validator = PatchValidator()

        patch_preparation_service = PatchPreparationService(
            patch_validator
        )

        def repository_context_factory(
            data: dict,
        ) -> RepositoryContextResult:
            return RepositoryContextResult(
                status=data["status"],
                files=[
                    RepositoryFileContext(
                        file_path=item["file_path"],
                        content=item["content"],
                        sha256=item["sha256"],
                    )
                    for item in data["files"]
                ],
                total_bytes=data["total_bytes"],
                skipped_files=data["skipped_files"],
                errors=data["errors"],
            )

        def execution_worker_factory(execution_service):
            patch_application_service = PatchApplicationService(
                sandbox_provider=sandbox_provider,
                patch_validator=patch_validator,
                integrity_verifier=FileIntegrityVerifier(
                    sandbox_provider
                ),
                post_application_verifier=PostApplicationVerifier(
                    sandbox_provider
                ),
                git_state_collector=GitStateCollector(
                    sandbox_provider
                ),
                git_change_verifier=GitChangeVerifier(),
            )

            return ApprovedPatchExecutionWorker(
                execution_service=execution_service,
                sandbox_provider=sandbox_provider,
                patch_application_service=patch_application_service,
                patch_builder=PatchBuilder,
                repository_context_factory=repository_context_factory,
                worker_id=f"forgeai-api-{uuid4()}",
            )

        # 10. Compile the complete LangGraph workflow.
        graph = build_agent_graph(
            planner_agent=planner_agent,
            researcher_agent=researcher_agent,
            coder_agent=coder_agent,
            reviewer_agent=reviewer_agent,
            sandbox_provider=sandbox_provider,
            sandbox_timeout_seconds=settings.e2b_sandbox_timeout,
            checkpointer=checkpointer,
            session_factory=SessionLocal,
            patch_preparation_service=patch_preparation_service,
            execution_worker_factory=execution_worker_factory,
            mcp_research_service=mcp_research_service,
            mcp_max_tool_calls=settings.mcp_max_tool_calls,
        )

        # 11. Expose application resources.
        app.state.graph = graph

        app.state.checkpointer = checkpointer
        app.state.checkpoint_pool = checkpoint_pool

        app.state.telemetry = telemetry

        app.state.mcp_enabled = settings.mcp_enabled
        app.state.mcp_client_manager = mcp_client_manager
        app.state.mcp_connection_service = mcp_connection_service
        app.state.mcp_research_service = mcp_research_service

        yield

    finally:
        # 12. Disconnect MCP servers before closing application resources.
        try:
            if mcp_connection_service is not None:
                await mcp_connection_service.disconnect_all()

        finally:
            # 13. Close the GitHub HTTP client.
            try:
                if github_client is not None:
                    await github_client.close()

            finally:
                # 14. Flush pending Langfuse events.
                try:
                    if telemetry is not None:
                        telemetry.flush()

                finally:
                    # 15. Close PostgreSQL and flush tracing.
                    try:
                        checkpoint_pool.close()
                    finally:
                        shutdown_tracing()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def trace_http_request(request, call_next):
    """Trace API requests without capturing credentials or request bodies."""
    tracer = trace.get_tracer("forgeai.http")

    with tracer.start_as_current_span("http.server.request") as span:
        span.set_attribute("http.request.method", request.method)
        span.set_attribute("http.route.path", request.url.path[:256])

        try:
            response = await call_next(request)

            span.set_attribute(
                "http.response.status_code",
                response.status_code,
            )

            if response.status_code >= 500:
                span.set_status(
                    Status(StatusCode.ERROR, "HTTP server error")
                )

            trace_id = span.get_span_context().trace_id

            if trace_id:
                response.headers["X-Trace-Id"] = f"{trace_id:032x}"

            return response

        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            raise


# Register API routers.
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(runs_router)
app.include_router(runs_collection_router)
app.include_router(github_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }
