# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

**Backend (Python/FastAPI):**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with OPENAI_API_KEY, GITHUB_TOKEN, and optional LANGCHAIN_* keys
uvicorn app.main:app --reload
# Runs on http://localhost:8000
```

**Frontend (React/Vite):**
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

**Full Stack (Docker):**
```bash
docker-compose up
```

## Architecture

### High-Level Design

This is a full-stack PR review automation system:

1. **Frontend (React/Vite)** — User interface for submitting PRs and viewing reviews. Communicates with the backend via REST API.

2. **Backend (FastAPI)** — Exposes REST endpoints for PR review requests. Routes requests through a LangGraph-based agent for processing.

3. **Agent Pipeline (LangGraph)** — Orchestrates the review workflow:
   - Receives PR details from API endpoint
   - Uses GitHub integration tools to fetch PR metadata and diffs
   - Invokes Claude API via LangChain for intelligent review generation
   - Returns structured review results

4. **External Integrations**:
   - **Claude API** (via LangChain/LangChain-OpenAI) — Performs the actual PR analysis and review generation
   - **GitHub API** — Fetches PR content, diffs, and metadata

### Directory Structure

- **backend/app/** — Main application code
  - `main.py` — FastAPI app initialization, CORS middleware, health endpoint
  - `routers/review.py` — Review API endpoints (POST /api/reviews, GET /api/reviews/{id}, etc.)
  - `agents/pr_agent.py` — LangGraph agent definition and review workflow (WIP)
  - `tools/github.py` — GitHub API integration functions (WIP)
  - `models/review.py` — Pydantic models for PR review request/response validation (WIP)

- **frontend/src/** — React application
  - `App.jsx` — Main component
  - Supporting React files for UI

### CORS and Local Development

The backend is configured to accept requests from `http://localhost:5173` (the frontend dev server). If you change the frontend port, update `app/main.py` CORSMiddleware `allow_origins`.

## Development Workflow

### Running Individual Services

**Backend alone:**
```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend alone:**
```bash
cd frontend && npm run dev
```

### Code Organization

- **API Endpoints** live in `routers/` — Each module should have a router exported via `__init__.py`
- **Data Models** in `models/` — Use Pydantic for request/response validation and type safety
- **Agent Logic** in `agents/` — LangGraph state graphs that define the workflow
- **Integrations** in `tools/` — Functions that interact with external APIs (GitHub, etc.)

### Environment Variables

Required for backend operation:
- `OPENAI_API_KEY` — Claude API key (required)
- `GITHUB_TOKEN` — GitHub token with `repo` scope (required)

Optional (for LangChain observability):
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_PROJECT`

### Tech Stack Notes

**Backend:**
- FastAPI 0.115.0 — Async-first, auto-generated OpenAPI docs at `/docs`
- LangChain 0.3.0 + LangGraph 0.2.28 — Agent framework; defines state machines for multi-step workflows
- Pydantic 2.9.2 — Request/response validation (use `model_validate()` for parsing)
- Python-dotenv — Loads `.env` into `os.environ`

**Frontend:**
- React 19 — Component library
- Vite 8 — Fast build tool with HMR; dev server on port 5173
- ESLint + Prettier — Code quality and formatting

### Linting & Formatting

**Backend:**
```bash
# Install (optional, not in requirements.txt yet)
pip install black flake8

# Format
black app/

# Lint
flake8 app/
```

**Frontend:**
```bash
# Lint and fix
npm run lint -- --fix
```

## Key Design Patterns

1. **Router-based API structure** — Each feature area (e.g., reviews) gets its own router module; routers are included in `main.py`.

2. **Agent-based workflow** — Complex PR analysis is handled by a LangGraph state graph in `pr_agent.py`, not by simple sequential calls. This allows for multi-step reasoning and tool use.

3. **Tool abstraction** — External API calls (GitHub) are wrapped in reusable tool functions that the agent can invoke.

4. **Pydantic models as contract** — Request/response shapes are validated by Pydantic models before reaching business logic.

## Docker Deployment Notes

- Backend container runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Frontend container runs Vite dev server; volumes mount source for live reload
- Both services expose their respective ports (8000, 5173)
- Backend depends on frontend service (in compose file) for startup ordering

## Common Tasks

- **Add an API endpoint:** Create a function in `routers/review.py`, decorate with `@router.post()` or `@router.get()`, ensure router is included in `main.py`
- **Add a tool for the agent:** Write function in `tools/github.py`, import and register with the LangGraph agent in `pr_agent.py`
- **Update data models:** Edit `models/review.py` using Pydantic syntax; changes are auto-validated on request/response
- **Modify the review workflow:** Edit the state graph definition in `agents/pr_agent.py`

## WIP Components

These are partially implemented and will need completion:

- `app/agents/pr_agent.py` — LangGraph agent definition needs to be fully built out with state, nodes, and edges
- `app/tools/github.py` — GitHub integration functions (fetch PR, get diff, etc.) not yet implemented
- `app/models/review.py` — Review request/response models not yet defined
- `app/routers/review.py` — Review endpoints stubbed but need integration with agent logic
- `frontend/src/` — React UI components need to be built
