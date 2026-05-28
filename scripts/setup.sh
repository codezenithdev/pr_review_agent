#!/bin/bash
# Setup script for PR Review Agent (macOS/Linux)
# Installs dependencies and configures environment

set -e  # Exit on error

echo "🔧 PR Review Agent Setup"
echo "========================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required"
    exit 1
fi

# API Setup
echo ""
echo "📦 Setting up API service..."
cd services/api

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "  Installing Python dependencies..."
pip install -q -r requirements.txt

# Setup .env file
if [ ! -f ".env" ]; then
    echo "  Creating .env file from template..."
    cp .env.example .env
    echo "  ⚠️  Please edit .env with your API keys:"
    echo "     • OPENAI_API_KEY (from https://console.anthropic.com/api_keys)"
    echo "     • GITHUB_TOKEN (from https://github.com/settings/tokens)"
else
    echo "  ✓ .env file already exists"
fi

cd ../..

# UI Setup
echo ""
echo "🎨 Setting up UI service..."
cd services/ui

# Install dependencies
echo "  Installing Python dependencies..."
pip install -q -r requirements.txt

cd ../..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit services/api/.env with your API keys"
echo "2. Run: ./scripts/run.sh"
echo ""
echo "For more info, see: README.md"
