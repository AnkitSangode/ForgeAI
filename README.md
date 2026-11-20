# ForgeAI — Autonomous AI Software Engineering Agent

<p align="center">
  <strong>From software engineering tasks to AI-assisted code execution.</strong>
</p>

<p align="center">
  An autonomous software engineering platform that uses specialized AI agents, repository intelligence, sandboxed execution, and human approval workflows to assist with real-world software development tasks.
</p>

<p align="center">
  <img src="docs/screenshots/forgeai-banner.png" alt="ForgeAI Banner" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/AnkitSangode/ForgeAI">GitHub Repository</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#screenshots">Screenshots</a>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [How ForgeAI Works](#how-forgeai-works)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [API Overview](#api-overview)
- [Agent Workflow](#agent-workflow)
- [Security and Human-in-the-Loop](#security-and-human-in-the-loop)
- [Deployment](#deployment)
- [Screenshots](#screenshots)
- [Limitations and Considerations](#limitations-and-considerations)
- [Future Improvements](#future-improvements)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Overview

**ForgeAI** is an AI-powered autonomous software engineering platform designed to assist developers with repository-level development tasks.

Instead of relying on a single LLM prompt to generate code, ForgeAI organizes software engineering activities into a multi-agent workflow.

The system is designed around specialized agents that can:

1. Understand a software engineering task.
2. Analyze the target GitHub repository.
3. Inspect relevant files and project structure.
4. Develop an implementation strategy.
5. Generate code changes.
6. Review proposed changes.
7. Execute supported operations inside an isolated sandbox.
8. Incorporate human approval into sensitive workflow stages.

ForgeAI combines agent orchestration, repository analysis, MCP-based tool integration, sandbox execution, and a web-based dashboard into one engineering workflow.

The goal is to move beyond simple code generation toward a more structured, observable, and controlled AI software engineering process.

## Problem Statement

Traditional AI coding assistants primarily operate through conversational interactions. Developers still need to manually coordinate repository inspection, implementation, testing, and validation.

This creates several challenges:

- Understanding large repositories before making changes.
- Maintaining context across multiple engineering steps.
- Coordinating different reasoning and implementation activities.
- Safely executing generated code.
- Reviewing AI-generated changes before accepting them.
- Tracking task execution and failures.

ForgeAI addresses these challenges through a structured agent architecture where specialized agents collaborate under a shared workflow.

## Key Features

### 1. Multi-Agent Software Engineering

ForgeAI uses specialized agents with distinct responsibilities.

| Agent | Responsibility |
|---|---|
| Planner | Understands the task and develops an execution plan |
| Researcher | Investigates repository context and gathers relevant information |
| Coder | Generates implementation changes |
| Reviewer | Evaluates proposed changes and identifies potential issues |

The agents work together through a coordinated workflow rather than operating as independent chat interfaces.

### 2. GitHub Repository Integration

ForgeAI is designed to work with existing GitHub repositories.

Capabilities include:

- Repository URL submission.
- Repository cloning.
- Repository inspection.
- Project structure analysis.
- File and code context gathering.
- Commit and revision verification.

### 3. Sandboxed Code Execution

ForgeAI uses **E2B** to provide an isolated execution environment for supported repository operations.

The sandbox architecture helps separate code execution from the application server.

Designed workflow:

- Create an execution sandbox.
- Clone the target repository.
- Inspect the project.
- Prepare repository context.
- Execute supported engineering operations.
- Validate changes before considering them complete.

### 4. MCP Tool Integration

ForgeAI incorporates the Model Context Protocol (MCP) to organize access to external tools.

The project includes MCP integrations for areas such as:

- Filesystem operations.
- PostgreSQL interactions.
- Web search.
- Browser automation with Playwright.

MCP provides a structured way to expose tools to agent workflows without tightly coupling every tool implementation to the agent's reasoning logic.

### 5. Human-in-the-Loop (HITL)

Autonomous execution should not mean unrestricted execution.

ForgeAI incorporates human approval into sensitive workflow stages.

The intended approval flow allows a human to inspect proposed actions and approve or reject them before the workflow proceeds.

### 6. Task and Execution Management

The dashboard provides a centralized interface for managing engineering tasks.

Core workflow:

- Create a task.
- Provide a task description.
- Connect a GitHub repository.
- Start an agent execution.
- Monitor execution status.
- Inspect task and run information.

### 7. Observability

ForgeAI includes optional observability integrations using Langfuse and OpenTelemetry.

These integrations are intended to help track:

- Agent execution.
- Workflow behavior.
- LLM interactions.
- Errors and failures.
- Execution traces.

Observability can be disabled when deploying a minimal demo configuration.

---

## How ForgeAI Works

The following illustrates the intended high-level execution lifecycle.

```mermaid
flowchart TD
    A[Developer Creates Task] --> B[FastAPI Backend]
    B --> C[LangGraph Orchestrator]
    C --> D[Planner Agent]
    D --> E[Researcher Agent]
    E --> F[Repository Context]
    F --> G[Coder Agent]
    G --> H[Reviewer Agent]
    H --> I{Human Approval Required?}
    I -->|Yes| J[Human Reviews Changes]
    J -->|Approved| K[E2B Sandbox Execution]
    J -->|Rejected| L[Return / Stop Workflow]
    I -->|No| K
    K --> M[Execution and Validation]
    M --> N[Update Run Status]
    N --> O[Dashboard]
```

*Note: The exact transitions and approval requirements depend on the configured workflow and task execution path.*

### Execution Lifecycle

**Step 1 — Task Creation**

The developer submits a task containing a title, description, and repository URL.

**Step 2 — Workflow Initialization**

The backend creates an execution record and initializes the agent workflow.

**Step 3 — Planning and Research**

The Planner and Researcher agents work on understanding the task and gathering relevant repository context.

**Step 4 — Implementation**

The Coder agent prepares implementation changes based on the available context.

**Step 5 — Review**

The Reviewer agent evaluates proposed changes and identifies potential problems.

**Step 6 — Approval and Execution**

Where configured, human approval is incorporated before sensitive execution operations.

Supported operations are carried out within the E2B sandbox.

**Step 7 — Status Tracking**

The backend updates the execution status, which can be retrieved through the frontend.

---

## Architecture

ForgeAI follows a modular architecture that separates the user interface, API layer, agent orchestration, external tools, and infrastructure.

```mermaid
flowchart TB
    U[Developer]
    subgraph Frontend
        A[Next.js Dashboard]
        B[Authentication]
        C[Task Management]
        D[Execution Monitoring]
    end

    subgraph Backend
        E[FastAPI]
        F[API and Service Layer]
        G[LangGraph Orchestrator]
        H[Agent State]
    end

    subgraph Agents
        I[Planner]
        J[Researcher]
        K[Coder]
        L[Reviewer]
    end

    subgraph Tools
        M[MCP Tool Registry]
        N[GitHub Integration]
        O[E2B Sandbox]
        P[Playwright / Web Search]
    end

    subgraph Infrastructure
        Q[(PostgreSQL)]
        R[LLM Provider]
        S[Langfuse / OpenTelemetry]
    end

    U --> A
    A --> B
    A --> C
    A --> D
    A --> E
    E --> F
    F --> G
    G <--> H
    G --> I
    G --> J
    G --> K
    G --> L
    I --> M
    J --> M
    K --> M
    L --> M
    M --> N
    M --> O
    M --> P
    F --> Q
    G --> R
    G --> S
```

### Architectural Responsibilities

| Component | Responsibility |
|---|---|
| Next.js | Frontend and user interaction |
| FastAPI | Backend API and request handling |
| SQLAlchemy | Database access and persistence |
| PostgreSQL | Application and execution data |
| LangGraph | Agent orchestration and workflow state |
| LLM Provider | Reasoning and code generation |
| MCP | Structured external tool integration |
| E2B | Isolated execution environment |
| GitHub | Repository access |
| Langfuse / OpenTelemetry | Optional observability |

---

## Technology Stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

### AI and Agent Orchestration

- LangGraph
- LangChain
- OpenAI-compatible LLM integration
- Ollama for local model execution

### Tooling and Infrastructure

- Model Context Protocol (MCP)
- E2B
- GitHub API
- Playwright
- PostgreSQL
- Docker
- Langfuse
- OpenTelemetry

---

## Project Structure

The repository is organized into frontend and backend applications.

```text
ForgeAI/
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── login/
│   │   ├── tasks/
│   │   │   ├── [taskId]/
│   │   │   └── new/
│   │   ├── reviews/
│   │   └── ...
│   │
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── src/
│   │   └── forgeai/
│   │       ├── api/
│   │       ├── agents/
│   │       ├── core/
│   │       ├── db/
│   │       ├── domain/
│   │       ├── llm/
│   │       ├── mcp/
│   │       ├── repositories/
│   │       ├── services/
│   │       └── ...
│   │
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── uv.lock
│   └── ...
│
├── docs/
│   └── screenshots/
│
├── README.md
└── ...
```

*The tree highlights the main application areas; individual module names may evolve as the project develops.*

---

## Getting Started

### Prerequisites

Install the following before running ForgeAI locally:

- Python 3.11
- Node.js and npm
- PostgreSQL
- Git
- uv package manager
- An LLM provider API key, or a locally running Ollama instance
- E2B API key for sandbox-based execution
- GitHub credentials for private repository access

### 1. Clone the Repository

```bash
git clone https://github.com/AnkitSangode/ForgeAI.git

cd ForgeAI
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Install dependencies:

```bash
uv sync
```

Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables in `.env`.

Run database migrations:

```bash
uv run alembic upgrade head
```

Start the backend:

```bash
uv run uvicorn forgeai.main:app --reload
```

The API should be available at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file:

```bash
cp .env.example .env.local
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

Configure the API URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Start the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## Environment Variables

Never commit actual API keys, database passwords, or authentication secrets to GitHub.

### Backend Environment

Configure the variables supported by your backend settings.

| Variable | Description |
|---|---|
| `ENVIRONMENT` | Application environment |
| `DATABASE_URL` | PostgreSQL connection URL |
| `JWT_SECRET_KEY` | Secret used for authentication tokens |
| `LLM_PROVIDER` | Selects the configured LLM provider |
| `OPENAI_API_KEY` | OpenAI API key when using OpenAI |
| `OPENAI_MODEL` | OpenAI model identifier |
| `E2B_API_KEY` | E2B sandbox API key |
| `MCP_ENABLED` | Enables or disables MCP integrations |
| `OTEL_ENABLED` | Enables or disables OpenTelemetry |
| `LANGFUSE_ENABLED` | Enables or disables Langfuse |
| `CORS_ORIGINS` | Allowed frontend origins |

Example local configuration:

```env
ENVIRONMENT=development

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/forgeai

JWT_SECRET_KEY=REPLACE_WITH_A_SECURE_SECRET

LLM_PROVIDER=ollama

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1

E2B_API_KEY=

MCP_ENABLED=false
OTEL_ENABLED=false
LANGFUSE_ENABLED=false

CORS_ORIGINS=http://localhost:3000
```

The exact variable names and optional settings should match the backend configuration in `backend/.env.example`.

### Frontend Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

For production, replace the local URL with your deployed backend API URL.

**Important:** Never expose backend secrets through `NEXT_PUBLIC_` variables. Next.js exposes those variables to browser-side code.

---

## Running the Application

Once both services are running:

1. Open the frontend.
2. Register an account.
3. Sign in.
4. Navigate to the task dashboard.
5. Create a new engineering task.
6. Enter a GitHub repository URL.
7. Open the created task.
8. Start an agent execution.
9. Monitor the execution status.

Example task:

```text
Title:
Fix authentication middleware

Description:
Inspect the authentication middleware in the repository.
Identify potential issues with token validation and expiration.
Propose and implement an appropriate fix.
Review the changes before execution.

Repository:
https://github.com/your-username/your-repository
```

Use a repository that you own or have permission to access.

---

## API Overview

ForgeAI exposes REST APIs through FastAPI.

The following endpoints represent the primary task and execution operations.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/tasks` | Create a task |
| GET | `/api/v1/tasks` | List tasks |
| GET | `/api/v1/tasks/{task_id}` | Retrieve a task |
| POST | `/api/v1/tasks/{task_id}/runs` | Start an agent run |
| GET | `/api/v1/tasks/{task_id}/runs` | List runs for a task |
| GET | `/api/v1/runs/{run_id}` | Retrieve an agent run |

Interactive API documentation is available through:

```text
/docs
```

### Example: Create a Task

```http
POST /api/v1/tasks
Content-Type: application/json
```

```json
{
  "title": "Fix authentication middleware",
  "description": "Inspect and fix the authentication middleware.",
  "repository_url": "https://github.com/your-username/your-repository"
}
```

*Authenticated endpoints require the appropriate access token.*

---

## Agent Workflow

ForgeAI uses specialized agents to separate software engineering responsibilities.

### Planner Agent

Responsible for understanding the task and developing an execution strategy.

### Researcher Agent

Responsible for investigating repository context, identifying relevant files, and gathering information needed for implementation.

### Coder Agent

Responsible for producing implementation changes based on the task and available repository context.

### Reviewer Agent

Responsible for evaluating proposed changes and identifying potential issues before execution or approval.

### Why a Multi-Agent Architecture?

A single LLM call often combines planning, research, coding, and review into one response.

This can make complex workflows difficult to control and debug.

A multi-agent approach provides:

- Separation of responsibilities.
- More structured reasoning.
- Better workflow visibility.
- Easier debugging of individual stages.
- Opportunities for human approval.
- A foundation for adding specialized agents.

LangGraph coordinates the workflow and manages the shared execution state.

---

## Security and Human-in-the-Loop

ForgeAI is designed with controlled execution in mind.

Important design considerations include:

- JWT-based authentication.
- Environment-based secret management.
- Isolated sandbox execution through E2B.
- Configurable MCP integrations.
- Human approval for sensitive operations.
- Separation between frontend and backend secrets.

### Important Security Consideration

The current demo deployment should not be treated as a fully production-hardened multi-tenant service.

Before production use, additional validation is required for:

- User-level task and run ownership enforcement.
- Authorization checks across all API operations.
- Durable background job execution.
- Sandbox resource limits and cleanup.
- Rate limiting and abuse prevention.
- Secret rotation and secure credential storage.
- Audit logging and execution trace retention.

---

## Deployment

The intended demo deployment architecture uses:

| Component | Platform |
|---|---|
| Frontend | Vercel |
| Backend | Render |
| Database | Neon PostgreSQL |
| LLM | OpenAI API |
| Code Sandbox | E2B |

### Frontend — Vercel

Deploy the `frontend` directory as a Next.js application.

Configure:

```env
NEXT_PUBLIC_API_URL=https://YOUR-RENDER-SERVICE.onrender.com/api/v1
```

### Backend — Render

Deploy the `backend` directory as a Python web service.

Example commands:

**Build:**

```bash
pip install uv && uv sync --frozen --no-dev
```

**Start:**

```bash
uv run uvicorn forgeai.main:app --host 0.0.0.0 --port $PORT
```

Configure the required backend environment variables in Render.

Set `CORS_ORIGINS` to the actual Vercel frontend origin.

### Database — Neon

Create a PostgreSQL project in Neon and configure the database connection string in the backend environment.

Use the connection format expected by the application's SQLAlchemy driver.

### Deployment Considerations

Free hosting plans can have usage restrictions, cold starts, and limited resources.

OpenAI inference and E2B sandbox usage may incur charges independently of the hosting plan.

---

## Screenshots

The following sections are reserved for actual application screenshots.

Replace the image paths with screenshots captured from the deployed application.

### 1. Landing Page

![ForgeAI Landing Page](docs/screenshots/01-landing-page.png)

### 2. Authentication

![ForgeAI Authentication](docs/screenshots/02-authentication.png)

### 3. Dashboard

![ForgeAI Dashboard](docs/screenshots/03-dashboard.png)

### 4. Create Engineering Task

![Create Task](docs/screenshots/04-create-task.png)

### 5. Task Details

![Task Details](docs/screenshots/05-task-details.png)

### 6. Agent Execution

![Agent Execution](docs/screenshots/06-agent-execution.png)

### 7. Human Approval / Code Review

![Human Approval](docs/screenshots/07-human-approval.png)

### 8. Architecture Overview

![ForgeAI Architecture](docs/screenshots/08-architecture.png)

---

## Limitations and Considerations

ForgeAI is an evolving engineering project.

The current implementation and demo configuration have some limitations:

- Local Ollama instances are not automatically accessible from cloud-hosted backend services.
- Cloud deployment requires an externally accessible LLM provider or separately hosted inference service.
- Render free services may sleep when idle.
- Background task execution is not equivalent to a durable distributed job queue.
- Some optional MCP and observability integrations may be disabled in the demo configuration.
- Not every dashboard section necessarily represents a fully connected backend workflow.
- Production-grade multi-user isolation and authorization require additional hardening.

These limitations should be considered before using the project for real production workloads.

---

## Future Improvements

Potential areas for further development include:

- [ ] Durable background job processing with Redis and Celery or an equivalent queue.
- [ ] Stronger multi-tenant authorization and organization-level isolation.
- [ ] Advanced repository indexing and semantic code search.
- [ ] Improved code diff visualization.
- [ ] Automated test execution and validation.
- [ ] More robust pull request creation and management.
- [ ] Advanced human approval workflows.
- [ ] More specialized engineering agents.
- [ ] Agent performance and cost analytics.
- [ ] Expanded observability and tracing.
- [ ] More self-hosted and open-source LLM options.
- [ ] Improved sandbox lifecycle and resource management.

---

## Contributing

Contributions, suggestions, and feedback are welcome.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Implement your changes.
4. Run relevant tests.
5. Submit a pull request with a clear description.

```bash
git checkout -b feature/your-feature-name

git add .

git commit -m "feat: add your feature"

git push origin feature/your-feature-name
```

---


## Author

**Ankit Naresh Sangode**

AI / ML Engineer | Generative AI | Agentic AI | Full-Stack Development

- GitHub: [@AnkitSangode](https://github.com/AnkitSangode)
- Project: [ForgeAI](https://github.com/AnkitSangode/ForgeAI)

---

<p align="center">
  <strong>ForgeAI — Engineering software with intelligent agents.</strong>
</p>

<p align="center">
  Built to explore the next generation of autonomous software engineering systems.
</p>