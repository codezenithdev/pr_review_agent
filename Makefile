.PHONY: help install setup-api setup-ui run-api run-ui run-all clean docs test

help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║        PR Review Agent - Development Commands                  ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install          Install all dependencies"
	@echo "  make setup-api        Setup API service"
	@echo "  make setup-ui         Setup UI service"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run-api          Start API service (port 8000)"
	@echo "  make run-ui           Start UI service (port 8501)"
	@echo "  make run-all          Start both services"
	@echo ""
	@echo "Development:"
	@echo "  make test             Run tests"
	@echo "  make clean            Clean cache and temp files"
	@echo "  make docs             Open documentation"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start services with Docker Compose"
	@echo "  make docker-down      Stop Docker services"
	@echo ""

install: setup-api setup-ui
	@echo "✅ All dependencies installed!"

setup-api:
	@echo "🔧 Setting up API service..."
	cd services/api && \
	python -m venv .venv && \
	pip install --upgrade pip && \
	pip install -r requirements.txt && \
	cp .env.example .env
	@echo "✅ API service ready! Edit services/api/.env with your keys."

setup-ui:
	@echo "🎨 Setting up UI service..."
	cd services/ui && \
	pip install -r requirements.txt
	@echo "✅ UI service ready!"

run-api:
	@echo "🚀 Starting API service on http://localhost:8000"
	cd services/api && \
	. .venv/Scripts/activate && \
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-ui:
	@echo "🎨 Starting UI service on http://localhost:8501"
	cd services/ui && \
	streamlit run app.py --server.port 8501

run-all:
	@echo "🚀 Starting all services..."
	@echo ""
	@echo "Starting API (port 8000)..."
	@echo "Starting UI (port 8501)..."
	@echo ""
	@echo "Open two terminals and run:"
	@echo "  Terminal 1: make run-api"
	@echo "  Terminal 2: make run-ui"
	@echo ""

clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".streamlit" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned!"

docs:
	@echo "📚 Documentation files:"
	@echo "  - docs/PROJECT_README.md"
	@echo "  - docs/SYSTEM_COMPLETE.md"
	@echo "  - docs/PHASE_5_QUICK_START.md"
	@echo "  - docs/PHASE_5_STREAMLIT_PLAN.md"

test-api:
	@echo "🧪 Testing API..."
	curl -X POST http://localhost:8000/api/review \
		-H "Content-Type: application/json" \
		-d '{"pr_url": "https://github.com/anthropics/anthropic-sdk-python/pull/180"}'

docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose -f config/docker/docker-compose.yml up

docker-down:
	@echo "🛑 Stopping Docker services..."
	docker-compose -f config/docker/docker-compose.yml down

.DEFAULT_GOAL := help
