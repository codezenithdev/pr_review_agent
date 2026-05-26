#!/bin/bash

# PR Review Agent - Startup Script
# This script sets up and starts both the API and UI services

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║      PR Review Agent - Startup Script                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

echo "✅ Python $(python3 --version | cut -d' ' -f2) detected"
echo ""

# Setup API service
echo "🔧 Setting up API service..."
cd services/api

if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
fi

echo "  Activating virtual environment..."
source .venv/bin/activate

echo "  Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
    echo "  ⚠️  Edit services/api/.env with your API keys!"
fi

cd ../..
echo "✅ API service ready!"
echo ""

# Setup UI service
echo "🎨 Setting up UI service..."
cd services/ui

echo "  Installing dependencies..."
pip install -q -r requirements.txt

cd ../..
echo "✅ UI service ready!"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              Setup Complete! Ready to Launch                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 To start the services, open two terminals:"
echo ""
echo "  Terminal 1 (API):"
echo "    cd services/api"
echo "    source .venv/bin/activate  # Windows: .venv\\Scripts\\activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (UI):"
echo "    cd services/ui"
echo "    streamlit run app.py"
echo ""
echo "📍 Then visit: http://localhost:8501"
echo ""
