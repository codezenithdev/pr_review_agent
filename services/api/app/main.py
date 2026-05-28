import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import review


def validate_environment():
    """Validate required environment variables on startup."""
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key from https://platform.openai.com/api-keys",
        "GITHUB_TOKEN": "GitHub personal access token with 'repo' scope"
    }

    missing = []
    for key, description in required_vars.items():
        if not os.getenv(key):
            missing.append(f"  • {key}: {description}")

    if missing:
        print("\n" + "=" * 70)
        print("❌ ERROR: Missing required environment variables")
        print("=" * 70)
        for item in missing:
            print(item)
        print("\nPlease set these in .env file before running the application.")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Validate format (basic checks)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-"):
        print(f"⚠️  WARNING: OPENAI_API_KEY doesn't look valid (should start with 'sk-' for OpenAI)")

    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token and not github_token.startswith("ghp_"):
        print(f"⚠️  WARNING: GITHUB_TOKEN doesn't look valid (should start with 'ghp_')")

    print("✅ Environment validation passed\n")


# Validate environment before creating app
validate_environment()

app = FastAPI(
    title="PR Review Agent",
    description="Automated code review system using LangGraph and OpenAI API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(review.router)
