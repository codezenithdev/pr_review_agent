# PR Review Agent - Web UI

Streamlit-based web interface for submitting GitHub PRs for automated code review.

## Quick Start

### 1. Install Dependencies
```bash
cd services/ui
pip install -r requirements.txt
```

### 2. Ensure API Service is Running
```bash
# In another terminal:
cd services/api
uvicorn app.main:app --reload --port 8000
```

### 3. Run Streamlit App
```bash
streamlit run app.py
```

Opens at: **http://localhost:8501**

## Features

- 🔍 Submit GitHub PR URLs for review
- ⏱️ Real-time progress streaming
- 📊 Beautiful results with metrics
- 💬 Expandable detailed comments
- 📥 Download reviews as JSON
- 🎯 Custom focus areas
- ✍️ Custom review instructions
- 📚 Review history during session
- 🏥 Backend health checking

## Architecture

```
Frontend (Streamlit)
    ↓
Session State Management
    ├─ current_pr_url
    ├─ current_review
    ├─ reviews (history)
    └─ backend_available
    ↓
API Integration
    ├─ POST /api/review/stream (SSE)
    └─ POST /api/review (sync fallback)
    ↓
Backend (FastAPI)
    ↓
LangGraph Agent
    ↓
OpenAI API (GPT-4) + GitHub API
```

## Configuration

Edit `.streamlit/config.toml` to customize:
- Colors and theme
- Server settings
- Logger levels

## Testing

1. Open http://localhost:8501
2. Enter: `https://github.com/anthropics/anthropic-sdk-python/pull/180`
3. Click "Review PR"
4. Watch real-time progress
5. View results

## Technology Stack

- **Streamlit 1.28.1** — Web UI framework
- **Requests 2.31.0** — HTTP client
- **HTTPX 0.25.0** — Advanced HTTP
- **Python 3.8+** — Language

## Next Steps

- See `docs/PHASE_5_QUICK_START.md` for installation guide
- See `docs/SYSTEM_COMPLETE.md` for architecture overview
- See `docs/PHASE_5_STREAMLIT_PLAN.md` for design details
