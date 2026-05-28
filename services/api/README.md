# PR Review Agent - API Service

FastAPI backend for automated GitHub PR code reviews powered by OpenAI GPT-4 and LangGraph.

## Quick Start

### 1. Install Dependencies
```bash
cd services/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY (for OpenAI GPT-4)
# - GITHUB_TOKEN (for GitHub API)
```

### 3. Run Server
```bash
uvicorn app.main:app --reload --port 8000
```

Server runs at: **http://localhost:8000**

API docs: **http://localhost:8000/docs**

## Architecture

```
app/
├── main.py              ← FastAPI application
├── agents/
│   └── pr_agent.py     ← LangGraph agent orchestration
├── models/
│   └── review.py       ← Pydantic data models
├── routers/
│   └── review.py       ← API endpoints
└── tools/
    └── github.py       ← GitHub API integration
```

## Endpoints

- **POST /api/review** — Submit PR for review (sync)
- **POST /api/review/stream** — Submit PR with real-time progress (SSE)
- **GET /api/review/{id}** — Check review status
- **GET /health** — Health check

## Environment Variables

**Required:**
- `OPENAI_API_KEY` — OpenAI API key (from https://platform.openai.com/api-keys)
- `GITHUB_TOKEN` — GitHub personal access token

**Optional (LangSmith):**
- `LANGCHAIN_TRACING_V2` — Enable tracing
- `LANGCHAIN_API_KEY` — LangSmith API key
- `LANGCHAIN_PROJECT` — Project name

## Testing

```bash
# Test with a real public PR
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/anthropics/anthropic-sdk-python/pull/180"}'
```

## Technology Stack

- **FastAPI 0.115.0** — REST API framework
- **LangGraph 0.2.28** — Agent orchestration
- **LangChain 0.3.0** — LLM integration
- **Pydantic 2.9.2** — Data validation
- **Python 3.10+** — Language

## Next Steps

- See `docs/PHASE_5_QUICK_START.md` for full setup guide
- See `docs/SYSTEM_COMPLETE.md` for architecture overview
