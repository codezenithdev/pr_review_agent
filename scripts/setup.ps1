# Setup script for PR Review Agent (Windows PowerShell)
# Installs dependencies and configures environment

$ErrorActionPreference = "Stop"

Write-Host "🔧 PR Review Agent Setup" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "✓ Python version: $pythonVersion" -ForegroundColor Green

# Verify Python 3.10+
$pythonCheck = python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python 3.10+ required" -ForegroundColor Red
    exit 1
}

# API Setup
Write-Host ""
Write-Host "📦 Setting up API service..." -ForegroundColor Cyan
Set-Location services/api

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "  Installing Python dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# Setup .env file
if (-not (Test-Path ".env")) {
    Write-Host "  Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "  ⚠️  Please edit .env with your API keys:" -ForegroundColor Yellow
    Write-Host "     • OPENAI_API_KEY (from https://console.anthropic.com/api_keys)" -ForegroundColor Yellow
    Write-Host "     • GITHUB_TOKEN (from https://github.com/settings/tokens)" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ .env file already exists" -ForegroundColor Green
}

Set-Location ../..

# UI Setup
Write-Host ""
Write-Host "🎨 Setting up UI service..." -ForegroundColor Cyan
Set-Location services/ui

# Install dependencies
Write-Host "  Installing Python dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

Set-Location ../..

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit services/api/.env with your API keys" -ForegroundColor White
Write-Host "2. Run: .\scripts\run.ps1" -ForegroundColor White
Write-Host ""
Write-Host "For more info, see: README.md" -ForegroundColor Gray
