# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PR Review Agent** is a full-stack application that automates GitHub PR code reviews using OpenAI's GPT-4 API and LangGraph agent orchestration. Users submit a PR URL through a web UI, the system fetches PR metadata and diffs from GitHub, analyzes the code with GPT-4, and returns a structured review with score, verdict, and detailed comments.

## Quick Start for Development

### One-Command Setup

**macOS/Linux:**
```bash
./scripts/setup.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

The setup script:
- Checks Python 3.10+ is installed
- Creates virtual environments for API and UI services
- Installs dependencies from requirements.txt
- Creates .env file (copy of .env.example)

### One-Command Run

After setup, start both services:

**macOS/Linux:**
```bash
./scripts/run.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\run.ps1
```

The run script:
- Activates virtual environments
- Starts FastAPI backend on port 8000
- Starts Streamlit UI on port 8501
- Waits for services to be ready
- Auto-restarts failed services
- Press Ctrl+C to stop all services

### Manual Setup (Alternative)

If you prefer manual setup or the scripts fail:

**Terminal 1 — API Service:**
```bash
cd services/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with OPENAI_API_KEY and GITHUB_TOKEN
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI Service:**
```bash
cd services/ui
pip install -r requirements.txt
streamlit run app.py
```

### Demo Mode (No API Keys Required)

Test the UI without real API keys by running the API with DEMO_MODE=true:

```bash
cd services/api
DEMO_MODE=true uvicorn app.main:app --reload --port 8000
# In another terminal:
cd services/ui
streamlit run app.py
```

The system returns mock reviews with realistic data, perfect for UI testing and demos.

## Architecture

### System Design

```
User (Streamlit UI)
    ↓ HTTP POST
API Gateway (FastAPI)
    ↓
LangGraph Agent Pipeline (5 nodes)
    ├─ fetch_pr_metadata    (GitHub API)
    ├─ fetch_pr_files       (GitHub API)
    ├─ fetch_pr_commits     (GitHub API)
    ├─ analyze_with_openai  (OpenAI GPT-4 via LangChain)
    └─ parse_response       (JSON → ReviewSummary)
    ↓
Database (SQLite/PostgreSQL)
    ↓
Response (JSON with score, verdict, comments)
```

### Folder Structure

**Backend:**
```
services/api/
├── app/
│   ├── main.py                   # FastAPI setup, CORS, health check
│   ├── agents/
│   │   └── pr_agent.py          # LangGraph agent state machine (5 nodes)
│   ├── routers/
│   │   └── review.py            # API endpoints
│   ├── models/
│   │   └── review.py            # Pydantic data models
│   ├── tools/
│   │   └── github.py            # GitHub API integration
│   ├── db.py                    # SQLAlchemy database models (ReviewRecord)
│   └── __init__.py
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── README.md
```

**Frontend:**
```
services/ui/
├── app.py                       # Streamlit app (UI, session state, API integration)
├── requirements.txt
└── README.md
```

**Scripts:**
```
scripts/
├── setup.sh                     # Setup script (macOS/Linux)
├── setup.ps1                    # Setup script (Windows)
├── run.sh                       # Run script (macOS/Linux)
└── run.ps1                      # Run script (Windows)
```

### Data Flow

1. **User Input** → Streamlit UI captures PR URL + optional focus areas/custom instructions
2. **API Request** → POST to `/api/review` or `/api/review/stream` (stream prefers real-time progress)
3. **Agent Nodes** (in sequence):
   - `fetch_pr_metadata`: GitHub API → PR title, author, stats, branches
   - `fetch_pr_files`: GitHub API → diffs for changed files (capped at 20, 4000 chars each)
   - `fetch_pr_commits`: GitHub API → commit messages (up to 10)
   - `analyze_with_openai`: LangChain ChatOpenAI (GPT-4) → JSON review response
   - `parse_response`: JSON parsing → `ReviewSummary` Pydantic model
4. **Persistent Storage** → Review stored in database (id, status, result, feedback)
5. **Streaming Response** → Server-Sent Events (SSE) emits progress messages + final JSON
6. **UI Render** → Streamlit displays score, verdict, strengths, critical issues, detailed comments

### Key Technologies

- **FastAPI 0.115.0** — REST API framework (async, auto OpenAPI docs at `/docs`)
- **Streamlit 1.28.1** — Web UI framework (server-rendered, session state)
- **LangGraph 0.2.28** — Agent orchestration (state graphs, node execution)
- **LangChain 0.3.0** — LLM framework; integrates OpenAI API and tool use
- **LangChain-OpenAI** — OpenAI API client for GPT-4 and other models
- **SQLAlchemy 2.0.25** — ORM for persistent review storage (SQLite/PostgreSQL)
- **Pydantic 2.9.2** — Request/response validation and type safety
- **HTTPX 0.27.2** — Async HTTP client (used in GitHub tools)
- **Python 3.10+**

## Environment Variables

**Required:**
- `OPENAI_API_KEY` — OpenAI API key (from https://platform.openai.com/api-keys)
- `GITHUB_TOKEN` — GitHub personal access token with `repo` scope

**Optional (Observability):**
- `LANGCHAIN_TRACING_V2=true` — Enable LangChain tracing
- `LANGCHAIN_API_KEY` — LangSmith API key
- `LANGCHAIN_PROJECT` — Project name for organization

**Optional (Database & Features):**
- `DATABASE_URL` — Database connection string (default: `sqlite:///./reviews.db`)
  - SQLite: `sqlite:///./reviews.db` (development, file-based)
  - PostgreSQL: `postgresql://user:password@localhost:5432/pr_review` (production)
- `DEMO_MODE=true` — Use mock data instead of real API calls (testing without keys)

Copy `.env.example` to `.env` in `services/api/` and fill in required variables before running.

## Common Commands

### Backend (services/api)

```bash
cd services/api

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install/update dependencies
pip install -r requirements.txt

# Run development server (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Run production server (no reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# View OpenAPI docs
# Open http://localhost:8000/docs in browser

# Test a real PR
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/anthropics/anthropic-sdk-python/pull/180"}'

# Run with demo mode (no API keys)
DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

### Frontend (services/ui)

```bash
cd services/ui

# Install/update dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py

# Run on custom port
streamlit run app.py --server.port 8502
```

### Full Stack

```bash
# One-command setup
./scripts/setup.sh      # macOS/Linux
.\scripts\setup.ps1     # Windows

# One-command run (both services)
./scripts/run.sh        # macOS/Linux
.\scripts\run.ps1       # Windows
```

## API Endpoints

- **POST /api/review** — Submit PR for review (blocks until complete; returns `ReviewResponse`)
- **POST /api/review/stream** — Submit PR with real-time progress (SSE; streams progress messages + final `ReviewSummary`)
- **GET /api/review/{review_id}** — Check review status by ID (returns `ReviewResponse`)
- **POST /api/review/{review_id}/feedback** — Submit user feedback (helpful/not helpful + optional comment)
- **GET /health** — Health check (returns `{"status": "ok"}`)

## Database Configuration

### Development (SQLite)

Default: file-based SQLite database at `reviews.db`

```bash
# No configuration needed, uses default
DATABASE_URL=sqlite:///./reviews.db  # default if not set
```

Tables are auto-created on first run. Database file persists reviews across app restarts.

### Production (PostgreSQL)

```bash
# Set DATABASE_URL before running
export DATABASE_URL=postgresql://user:password@hostname:5432/pr_review

# Then start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

SQLAlchemy automatically detects the database type and configures the engine accordingly. Tables are created via `Base.metadata.create_all()` on module import.

## Development Patterns

### Adding a New Review Dimension

To add a new review focus area (e.g., "accessibility"):

1. Update `REVIEW_SYSTEM_PROMPT` in `services/api/app/agents/pr_agent.py` — add evaluation criteria
2. Update `focus_areas` multiselect in `services/ui/app.py` — add to the list
3. Test via UI: select the new focus area and run a review

### Modifying the Agent Workflow

The LangGraph state machine (`services/api/app/agents/pr_agent.py`):
- **State shape**: `AgentState` TypedDict defines all fields flowing through nodes
- **Nodes**: async functions that transform state and return modified state
- **Edges**: define node sequence (currently linear: metadata → files → commits → analyze → parse)

To add a new node (e.g., fetch discussion comments):
1. Create async function `async def node_fetch_pr_discussions(state: AgentState) -> AgentState`
2. Add to graph: `graph.add_node("fetch_discussions", node_fetch_pr_discussions)`
3. Insert into edge sequence: `graph.add_edge("fetch_commits", "fetch_discussions")`
4. Update final edge to point to the new node or the next node

### Adding a GitHub API Tool

New tools go in `services/api/app/tools/github.py` as `@tool`-decorated functions:

```python
@tool
def fetch_pr_reviews(pr_url: str) -> dict:
    """Fetch existing reviews for a PR."""
    owner, repo, pr_number = _extract_pr_url_parts(pr_url)
    # Make API call...
    return {"reviews": [...], "review_count": n}
```

Then import and use in `pr_agent.py`:
```python
result = fetch_pr_reviews.invoke({"pr_url": state["request"].pr_url})
```

### Data Model Changes

Pydantic models live in `services/api/app/models/review.py`. Updating them:

1. Add or modify fields in the class (use `Field(...)` for descriptions)
2. Add validators with `@field_validator` if needed
3. Update docstrings referencing the model (in agent prompts, etc.)
4. Test with a POST request to `/api/review` — FastAPI auto-validates

## CORS Configuration

The FastAPI app (`services/api/app/main.py`) accepts requests from:
- `http://localhost:8501` (Streamlit default port)
- `http://localhost:5173` (Vite default, kept for compatibility)

Update `CORSMiddleware` configuration if changing the frontend URL or adding production domains.

## Architecture Notes

**MVP Design Decisions:**
- **Persistent storage with SQLAlchemy**: Reviews stored in database (SQLite for dev, configurable for prod). Survives app restarts.
- **Linear agent workflow**: Nodes execute sequentially. No branching or conditional logic yet.
- **Graceful partial failures**: If GitHub API calls fail (e.g., can't fetch files), the agent continues with partial data rather than failing entirely.
- **Token limits**: File diffs capped at 4000 chars each; up to 20 files; commits capped at 10. Keeps OpenAI API cost and latency reasonable.
- **No authentication**: API endpoints are open (no API key validation). Can be added as needed.
- **Demo mode**: DEMO_MODE env var disables external API calls for UI testing without credentials.

**Future Improvements (Post-MVP):**
- Add background job queue for scalability
- Add API authentication and rate limiting
- Implement conditional agent edges (e.g., skip file fetch if no changes)
- Integrate with GitHub for auto-commenting on PRs
- Add retry logic for transient GitHub API failures
- Cache PR metadata to avoid re-fetching

## Debugging

**API Issues:**
1. Check server is running: `curl http://localhost:8000/health`
2. View OpenAPI docs: http://localhost:8000/docs
3. Check logs in terminal where server is running
4. Verify environment variables are set: `echo $GITHUB_TOKEN` (or PowerShell: `$env:GITHUB_TOKEN`)
5. Check database connectivity if using PostgreSQL

**Agent Issues:**
1. Add logging statements in agent nodes (`services/api/app/agents/pr_agent.py`)
2. Check LangSmith traces if `LANGCHAIN_TRACING_V2=true` is set
3. Test GitHub tools directly in Python REPL:
   ```python
   from services.api.app.tools.github import fetch_pr_metadata
   result = fetch_pr_metadata.invoke({"pr_url": "https://github.com/..."})
   print(result)
   ```

**UI Issues:**
1. Check backend is reachable: Streamlit sidebar shows "Backend connected" or error
2. Open browser console (F12) for JavaScript errors
3. Check Streamlit logs in terminal where it's running
4. Verify API service is running on port 8000

**Database Issues:**
1. SQLite: Check `reviews.db` file exists in `services/api/`
2. PostgreSQL: Verify connection string in `DATABASE_URL` env var
3. Check SQLAlchemy logs for migration or schema errors

## Testing the System

**Option 1: Via Streamlit UI (Recommended)**
1. Run setup and start scripts
2. Open http://localhost:8501
3. Enter a public GitHub PR URL (e.g., `https://github.com/anthropics/anthropic-sdk-python/pull/180`)
4. Click "Review PR"
5. Watch real-time progress, view results

**Option 2: Via FastAPI Swagger UI**
1. Open http://localhost:8000/docs
2. Expand the "POST /api/review" endpoint
3. Fill in the request body with a PR URL
4. Click "Execute"

**Option 3: Via cURL (API)**
```bash
curl -X POST http://localhost:8000/api/review/stream \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/anthropics/anthropic-sdk-python/pull/180",
    "focus_areas": ["security", "performance"],
    "custom_prompt": null
  }'
```

**Option 4: Demo Mode (No API Keys)**
```bash
cd services/api
DEMO_MODE=true uvicorn app.main:app --reload --port 8000

# Then open http://localhost:8501 and submit any PR URL
```

## File Locations Reference

| Purpose | Location |
|---------|----------|
| API startup | `services/api/app/main.py` |
| Agent orchestration | `services/api/app/agents/pr_agent.py` |
| API endpoints | `services/api/app/routers/review.py` |
| Data models | `services/api/app/models/review.py` |
| Database models | `services/api/app/db.py` |
| GitHub integration | `services/api/app/tools/github.py` |
| Streamlit UI | `services/ui/app.py` |
| Setup script | `scripts/setup.sh` or `scripts/setup.ps1` |
| Run script | `scripts/run.sh` or `scripts/run.ps1` |
| OpenAPI docs | http://localhost:8000/docs (auto-generated) |
| Review system prompt | `services/api/app/agents/pr_agent.py:REVIEW_SYSTEM_PROMPT` |
