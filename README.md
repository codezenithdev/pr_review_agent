# 🔍 PR Review Agent

> Automated code review system using Open AI, LangGraph, and GitHub integration

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red.svg)](https://streamlit.io/)

## Features

🤖 **AI-Powered Reviews**
- Automated code analysis using Open AI
- Structured review with score, verdict, and detailed comments
- Customizable focus areas (security, performance, maintainability, etc.)

⚡ **Real-Time Streaming**
- Live progress updates via Server-Sent Events (SSE)
- Watch review progress in real-time
- Beautiful UI with metrics and detailed findings

🔗 **GitHub Integration**
- Fetch PR metadata, diffs, and commit messages automatically
- Works with public and private repositories
- Graceful handling of API rate limits

📊 **Observability & Feedback**
- LangSmith integration for trace collection
- User feedback collection for model improvement
- Production-ready error handling and logging

💾 **Persistent Storage**
- SQLite for development, PostgreSQL for production
- Reviews persist across app restarts
- Feedback tracking for analytics

🎭 **Demo Mode**
- Test the full UI without API keys
- Mock reviews for development and demos
- Perfect for onboarding and testing

## Quick Start

### Prerequisites
- Python 3.10 or higher
- GitHub personal access token ([create one](https://github.com/settings/tokens))
- OpenAI API key ([get one](https://platform.openai.com/settings/organization/api-keys))
- Node.js 16+ (optional, for frontend development)

### One-Command Setup

**On macOS/Linux:**
```bash
./scripts/setup.sh
```

**On Windows (PowerShell):**
```powershell
.\scripts\setup.ps1
```

**Manual Setup:**

1. **Clone and navigate:**
```bash
cd pr_review_agent
```

2. **Create environment file:**
```bash
cp services/api/.env.example services/api/.env
```

3. **Edit `.env` with your API keys:**
```bash
# services/api/.env
OPENAI_API_KEY=sk-your-openai-api-key-here
GITHUB_TOKEN=ghp_your-github-token-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your-langsmith-key
LANGCHAIN_PROJECT=pr-review-agent
```

4. **Install dependencies and start services:**

**Terminal 1 - API Service:**
```bash
cd services/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - UI Service:**
```bash
cd services/ui
pip install -r requirements.txt
streamlit run app.py
```

5. **Open the UI:**
   - Navigate to http://localhost:8501
   - Enter a public GitHub PR URL
   - Click "Review PR" and watch real-time analysis

## Usage

### Via Web UI (Recommended)

1. **Submit a PR:**
   - Paste GitHub PR URL (e.g., `https://github.com/owner/repo/pull/123`)
   - Optionally select focus areas (security, performance, etc.)
   - Add custom instructions if needed

2. **Watch progress:**
   - Real-time status updates as review progresses
   - See metrics and findings as they arrive

3. **Review results:**
   - Overall score and verdict
   - Strengths and critical issues
   - Detailed comments with file/line info
   - Export as JSON

4. **Submit feedback:**
   - Rate the review (helpful/not helpful)
   - Add optional comments
   - Data sent to LangSmith for model improvement

### Via API (cURL)

**Sync endpoint (blocks until complete):**
```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "focus_areas": ["security", "performance"],
    "custom_prompt": null
  }'
```

**Stream endpoint (real-time progress):**
```bash
curl -X POST http://localhost:8000/api/review/stream \
  -H "Content-Type: application/json" \
  -d '{
    "pr_url": "https://github.com/owner/repo/pull/123",
    "focus_areas": ["security"],
    "custom_prompt": null
  }'
```

**Get review by ID:**
```bash
curl http://localhost:8000/api/review/{review_id}
```

**Submit feedback:**
```bash
curl -X POST http://localhost:8000/api/review/{review_id}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "helpful": true,
    "comment": "Great analysis!"
  }'
```

### Demo Mode (No API Keys Required)

Test the UI without API keys:

```bash
# Terminal 1
cd services/api
DEMO_MODE=true uvicorn app.main:app --reload --port 8000

# Terminal 2
cd services/ui
streamlit run app.py
```

The system will return mock reviews with realistic data.

## API Endpoints

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| `POST` | `/api/review` | Submit PR for review | `ReviewResponse` with status |
| `GET` | `/api/review/{id}` | Poll review status | `ReviewResponse` with result |
| `POST` | `/api/review/stream` | Stream review progress | SSE events + final result |
| `POST` | `/api/review/{id}/feedback` | Submit user feedback | `{status: "feedback_recorded"}` |
| `GET` | `/health` | Health check | `{status: "ok"}` |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Web Browser)                       │
│                    http://localhost:8501                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit UI (Python)                      │
│                  services/ui/app.py (410 lines)              │
│  • Input validation  • Progress streaming  • Results display │
│  • Feedback buttons  • JSON export  • Review history         │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│              services/api/app/main.py (40 lines)             │
│        CORS | Health check | Router registration            │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
    ┌────────┐   ┌──────────────┐   ┌────────────┐
    │ Router │   │ LangGraph    │   │ Database   │
    │(review)│   │ Agent (5 nodes)  │ (SQLite)   │
    └────┬───┘   └──────┬───────┘   └────────────┘
         │               │
         └───────┬───────┘
                 ↓
    ┌────────────────────────────────┐
    │  External APIs                 │
    ├────────────────────────────────┤
    │ • OpenAI API (code analysis)   │
    │ • GitHub API (PR data)         │
    │ • LangSmith (tracing/feedback) │
    └────────────────────────────────┘
```

### Component Breakdown

**Backend (services/api/)**
- `app/main.py` — FastAPI setup, CORS, health endpoint
- `app/routers/review.py` — 4 API endpoints
- `app/agents/pr_agent.py` — LangGraph 5-node orchestration
- `app/models/review.py` — Pydantic request/response schemas
- `app/tools/github.py` — GitHub API integration
- `app/db.py` — SQLAlchemy database models

**Frontend (services/ui/)**
- `app.py` — Complete Streamlit application (410 lines)
- Session state management
- Real-time progress streaming
- Review history tracking

## Environment Variables

### Required
- `OPENAI_API_KEY` — OpenAI API key (starts with `sk-`)
- `GITHUB_TOKEN` — GitHub personal access token (starts with `ghp_`)

### Optional (LangSmith Observability)
- `LANGCHAIN_TRACING_V2=true` — Enable tracing
- `LANGCHAIN_API_KEY` — LangSmith API key
- `LANGCHAIN_PROJECT` — Project name for organization

### Optional (Phase 7)
- `DATABASE_URL` — Database connection string (default: `sqlite:///./reviews.db`)
- `DEMO_MODE=true` — Use mock data instead of API calls

## Running the Full Stack

### All-in-One Script

**macOS/Linux:**
```bash
./scripts/run.sh
```

**Windows (PowerShell):**
```powershell
.\scripts\run.ps1
```

### Docker Compose

```bash
docker-compose -f config/docker/docker-compose.yml up
```

Both services start on:
- **API:** http://localhost:8000 (OpenAPI docs at `/docs`)
- **UI:** http://localhost:8501

## Testing

### Test a Real PR

1. Find a public GitHub PR (e.g., from [anthropic/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python/pulls))
2. Copy the PR URL
3. Paste in UI at http://localhost:8501
4. Click "Review PR"

### Test with Demo Mode

```bash
cd services/api
DEMO_MODE=true uvicorn app.main:app --reload --port 8000
```

Then submit any PR URL — you'll get mock data with realistic findings.

### Run Tests

```bash
cd services/api
pip install pytest
pytest tests/ -v
```

## Configuration

### Focus Areas

Available review dimensions (customizable in UI):
- **Security** — Vulnerabilities, auth, data protection
- **Performance** — Optimization, scalability, efficiency
- **Maintainability** — Code clarity, structure, best practices
- **Testability** — Test coverage, test quality
- **Best Practices** — Language idioms, modern patterns

### Review Scoring

Scores are 0-100:
- **90-100** — Excellent (✅ Approve)
- **75-89** — Good (⚠️ Approve with suggestions)
- **60-74** — Fair (🔴 Request changes)
- **Below 60** — Needs work (💬 Comment)

## Troubleshooting

### Backend won't start
```
❌ ERROR: Missing required environment variables: OPENAI_API_KEY, GITHUB_TOKEN

✅ Solution: Check .env file and add your API keys
```

### "Review not found" error
```
❌ 404: Review {review_id} not found

✅ Solution: Check review_id is correct, or use /api/review/stream for new reviews
```

### Streamlit connection error
```
❌ Backend unavailable (http://localhost:8000)

✅ Solution: Make sure API service is running on port 8000
```

### GitHub API rate limit
```
❌ GitHub API rate limited. Try again in an hour.

✅ Solution: Create a GitHub token with proper scope or wait for rate limit reset
```

### OpenAI API authentication failed
```
❌ OpenAI API authentication failed. Check OPENAI_API_KEY in .env file.

✅ Solution: Verify API key starts with 'sk-' and is valid from https://platform.openai.com/api-keys
```

## Development

### Project Structure
```
pr_review_agent/
├── services/
│   ├── api/                          # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py              # App setup & validation
│   │   │   ├── agents/pr_agent.py   # LangGraph orchestration
│   │   │   ├── routers/review.py    # API endpoints
│   │   │   ├── models/review.py     # Data models
│   │   │   ├── tools/github.py      # GitHub integration
│   │   │   └── db.py                # Database config
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md
│   │
│   └── ui/                           # Streamlit frontend
│       ├── app.py                   # Main UI (410 lines)
│       ├── requirements.txt
│       └── README.md
│
├── docs/                             # Documentation
│   ├── ROADMAP_PHASES_5_7.md
│   ├── PHASE_5_COMPLETE.md
│   └── README.md
│
├── scripts/                          # Setup & run scripts
│   ├── setup.sh
│   ├── setup.ps1
│   ├── run.sh
│   └── run.ps1
│
├── config/                           # Configuration
│   └── docker/
│       └── docker-compose.yml
│
├── CLAUDE.md                         # Development guide
└── README.md                         # This file
```

### Adding a New Review Dimension

1. Update `REVIEW_SYSTEM_PROMPT` in `services/api/app/agents/pr_agent.py`
2. Add to focus areas in `services/ui/app.py` multiselect
3. Test via UI

### Adding a GitHub API Tool

1. Create function in `services/api/app/tools/github.py` with `@tool` decorator
2. Import and use in `services/api/app/agents/pr_agent.py`
3. Add to LangGraph graph if needed

## Performance

- **Average review time:** 30-60 seconds (depends on PR size)
- **File diff limit:** 4,000 chars per file (capped)
- **Files analyzed:** Up to 20 files
- **Commits analyzed:** Up to 10 commits
- **Database:** SQLite for dev, PostgreSQL for prod
- **Caching:** GitHub metadata cached locally

## Production Deployment

### Environment Setup
```bash
# .env for production
OPENAI_API_KEY=sk-prod-key-here
GITHUB_TOKEN=ghp-prod-token-here
DATABASE_URL=postgresql://user:pass@db.example.com/pr_review
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-prod-key
LANGCHAIN_PROJECT=pr-review-agent-prod
```

### Database Migration
```bash
# Use PostgreSQL instead of SQLite
DATABASE_URL=postgresql://user:password@localhost:5432/pr_review
```

### Docker Deployment
```bash
docker-compose -f config/docker/docker-compose.yml up -d
```

## Future Improvements

- [ ] Background job queue for scalability
- [ ] API authentication and rate limiting
- [ ] Auto-comment on GitHub PRs
- [ ] Webhook integration for automatic reviews
- [ ] Web UI with React/Next.js
- [ ] Mobile app support
- [ ] Multi-language code analysis
- [ ] Custom review templates
- [ ] Review history analytics dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- 📖 Read [CLAUDE.md](CLAUDE.md) for development guide
- 📋 Check [docs/](docs/) for detailed documentation
- 🐛 Open an issue for bugs or feature requests
- 💬 Start a discussion for questions

## Acknowledgments

Built with:
- [OpenAI API](https://platform.openai.com) — Code analysis via GPT-4
- [LangGraph](https://langchain.com/langgraph) — Agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) — REST API
- [Streamlit](https://streamlit.io/) — Web UI
- [GitHub API](https://docs.github.com/en/rest) — PR data

---

**Made with ❤️ for better code reviews**

Last updated: May 28, 2026
