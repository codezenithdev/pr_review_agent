#!/bin/bash
# Run script for PR Review Agent (macOS/Linux)
# Starts both API and UI services in parallel

set -e

echo "🚀 PR Review Agent - Starting Services"
echo "======================================"

# Check if setup was run
if [ ! -f "services/api/.env" ]; then
    echo "❌ .env file not found. Please run setup first:"
    echo "   ./scripts/setup.sh"
    exit 1
fi

# Function to clean up on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID $UI_PID 2>/dev/null || true
    wait $API_PID $UI_PID 2>/dev/null || true
    echo "✅ Services stopped"
}

trap cleanup EXIT INT TERM

# Start API service
echo ""
echo "📡 Starting API service (port 8000)..."
cd services/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 > /tmp/api.log 2>&1 &
API_PID=$!
cd ../..

# Wait for API to be ready
echo "  Waiting for API to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✓ API is ready"
        break
    fi
    sleep 1
done

# Start UI service
echo ""
echo "🎨 Starting UI service (port 8501)..."
cd services/ui
streamlit run app.py --server.port 8501 > /tmp/ui.log 2>&1 &
UI_PID=$!
cd ../..

# Wait for UI to be ready
echo "  Waiting for UI to start..."
for i in {1..30}; do
    if curl -s http://localhost:8501 > /dev/null 2>&1; then
        echo "  ✓ UI is ready"
        break
    fi
    sleep 1
done

echo ""
echo "✅ All services started!"
echo ""
echo "🌐 Open your browser:"
echo "   • UI:  http://localhost:8501"
echo "   • API: http://localhost:8000/docs"
echo ""
echo "📝 View logs:"
echo "   • API: tail -f /tmp/api.log"
echo "   • UI:  tail -f /tmp/ui.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for background processes
wait
