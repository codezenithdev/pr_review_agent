# PR Review Agent

A full-stack application that leverages LangGraph and LangChain to provide automated PR reviews using OpenAI API.

## Project Structure

```
pr-review-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app & CORS setup
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── pr_agent.py       # LangGraph agent (WIP)
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   └── github.py         # GitHub integration tools (WIP)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── review.py         # Data models (WIP)
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── review.py         # Review API endpoints (WIP)
│   ├── .venv/                    # Python virtual environment
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Environment variables template
│   └── Dockerfile                # Container config
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Main React component
│   │   └── ...                   # Other React files
│   ├── package.json              # Node dependencies
│   └── vite.config.js            # Vite configuration
├── docker-compose.yml            # Multi-container orchestration
└── README.md                      # This file
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Create virtual environment and install dependencies:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your API keys:
   # - OPENAI_API_KEY: Get from https://platform.openai.com/api-keys
   # - GITHUB_TOKEN: Generate from https://github.com/settings/tokens
   # - LANGCHAIN_API_KEY: Get from https://smith.langchain.com (optional, for tracing)
   ```

3. **Start the backend server:**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload
   ```
   Backend runs on `http://localhost:8000`
   Health check: `curl http://localhost:8000/health`

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the dev server:**
   ```bash
   npm run dev
   ```
   Frontend runs on `http://localhost:5173`

## Environment Variables

Create a `backend/.env` file based on `backend/.env.example`:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for Open AI access | Yes |
| `GITHUB_TOKEN` | GitHub token for PR access | Yes |
| `LANGCHAIN_TRACING_V2` | Enable LangChain tracing | No (set `true` to debug) |
| `LANGCHAIN_API_KEY` | LangChain API key for tracing | No |
| `LANGCHAIN_PROJECT` | LangChain project name | No |

### Where to get API keys:
- **OpenAI API Key:** https://platform.openai.com/api-keys
- **GitHub Token:** https://github.com/settings/tokens (select `repo` scope for PR access)
- **LangChain API Key:** https://smith.langchain.com (optional, for debugging/monitoring)

## Docker Deployment

Run both services with Docker Compose:

```bash
docker-compose up
```

This starts:
- Backend on `http://localhost:8000`
- Frontend on `http://localhost:5173`

## API Endpoints

### Health Check
- **GET** `/health` — Returns `{"status": "ok"}`

### Review (WIP)
- **POST** `/api/reviews` — Submit a PR for review (coming soon)
- **GET** `/api/reviews/{id}` — Get review status (coming soon)

## Tech Stack

**Backend:**
- FastAPI 0.115.0 — Modern Python web framework
- LangChain 0.3.0 — LLM orchestration
- LangGraph 0.2.28 — Agent/workflow state management
- Pydantic 2.9.2 — Data validation
- Python-dotenv 1.0.1 — Environment configuration

**Frontend:**
- React 18 — UI framework
- Vite 8.0.14 — Build tool & dev server

## Development

### Running Tests
```bash
# Backend (TBD)
cd backend && pytest

# Frontend (TBD)
cd frontend && npm test
```

### Code Style
- Backend: Follow PEP 8 (use tools like `black`, `flake8`)
- Frontend: ESLint + Prettier (configured in `frontend/`)

## Next Steps

1. Implement GitHub PR fetching in `app/tools/github.py`
2. Build PR review LangGraph agent in `app/agents/pr_agent.py`
3. Define Pydantic models in `app/models/review.py`
4. Create API endpoints in `app/routers/review.py`
5. Build React UI in `frontend/src/`

## License

MIT
