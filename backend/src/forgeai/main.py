
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
from forgeai.api.health import router as health_router
from forgeai.api.tasks import router as tasks_router
from forgeai.api.runs import router as runs_router
from forgeai.core.config import get_settings
from forgeai.execution.sandbox.e2b_provider import E2BSandboxProvider
from forgeai.llm.llm_service import LLMService
from forgeai.llm.openai_provider import OpenAIProvider


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage long-lived application resources.

    Startup:
    - Initialize PostgreSQL checkpoint connection pool.
    - Initialize LangGraph Postgres checkpointer.
    - Construct shared LLM and agent dependencies.
    - Construct the E2B sandbox provider.
    - Compile the agent graph.

    Shutdown:
    - Close the checkpoint connection pool.
    """

    if settings.e2b_api_key is None:
        raise RuntimeError(
            "E2B_API_KEY must be configured before starting ForgeAI."
        )

    # Convert SQLAlchemy's URL into a psycopg-compatible connection string.
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

    try:
        # 1. Open the PostgreSQL connection pool.
        checkpoint_pool.open(wait=True)

        # 2. Initialize the LangGraph PostgreSQL checkpointer.
        checkpointer = PostgresSaver(checkpoint_pool)
        checkpointer.setup()

        # 3. Construct one shared LLM service.
        llm_provider = OpenAIProvider(settings)
        llm_service = LLMService(provider=llm_provider)

        # 4. Construct the agents using the shared LLM service.
        planner_agent = PlannerAgent(llm_service)
        researcher_agent = ResearcherAgent(llm_service)
        coder_agent = CoderAgent(llm_service)
        reviewer_agent = ReviewerAgent(llm_service)

        # 5. Construct the sandbox provider.
        sandbox_provider = E2BSandboxProvider(settings)

        # 6. Compile the graph with persistent checkpointing.
        graph = build_agent_graph(
            planner_agent=planner_agent,
            researcher_agent=researcher_agent,
            coder_agent=coder_agent,
            reviewer_agent=reviewer_agent,
            sandbox_provider=sandbox_provider,
            sandbox_timeout_seconds=settings.e2b_sandbox_timeout,
            checkpointer=checkpointer,
        )

        # 7. Make application resources available to API routes.
        app.state.graph = graph
        app.state.checkpointer = checkpointer
        app.state.checkpoint_pool = checkpoint_pool

        yield

    finally:
        # 8. Release the long-lived database resource.
        checkpoint_pool.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(auth_router)
app.include_router(approvals_router)
app.include_router(runs_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }
