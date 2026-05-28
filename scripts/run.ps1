# Run script for PR Review Agent (Windows PowerShell)
# Starts both API and UI services

$ErrorActionPreference = "Stop"

Write-Host "🚀 PR Review Agent - Starting Services" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Check if setup was run
if (-not (Test-Path "services/api/.env")) {
    Write-Host "❌ .env file not found. Please run setup first:" -ForegroundColor Red
    Write-Host "   .\scripts\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Function to clean up on exit
$cleanup = {
    Write-Host ""
    Write-Host "🛑 Shutting down services..." -ForegroundColor Yellow

    # Try to stop processes
    if ($null -ne $apiProcess) {
        try { Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
    if ($null -ne $uiProcess) {
        try { Stop-Process -Id $uiProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    }

    Write-Host "✅ Services stopped" -ForegroundColor Green
}

# Register cleanup on exit
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanup

# Start API service
Write-Host ""
Write-Host "📡 Starting API service (port 8000)..." -ForegroundColor Cyan
Set-Location services/api
& ".\.venv\Scripts\Activate.ps1"
$apiProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --reload --port 8000" -PassThru -WindowStyle Minimized
Set-Location ../..

# Wait for API to be ready
Write-Host "  Waiting for API to start..." -ForegroundColor Yellow
$apiReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
        Write-Host "  ✓ API is ready" -ForegroundColor Green
        $apiReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $apiReady) {
    Write-Host "  ⚠️  API might not be ready yet, continuing..." -ForegroundColor Yellow
}

# Start UI service
Write-Host ""
Write-Host "🎨 Starting UI service (port 8501)..." -ForegroundColor Cyan
Set-Location services/ui
$uiProcess = Start-Process -FilePath "streamlit" -ArgumentList "run app.py --server.port 8501" -PassThru -WindowStyle Minimized
Set-Location ../..

# Wait for UI to be ready
Write-Host "  Waiting for UI to start..." -ForegroundColor Yellow
$uiReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8501" -ErrorAction SilentlyContinue
        Write-Host "  ✓ UI is ready" -ForegroundColor Green
        $uiReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $uiReady) {
    Write-Host "  ⚠️  UI might not be ready yet, continuing..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Open your browser:" -ForegroundColor Cyan
Write-Host "   • UI:  http://localhost:8501" -ForegroundColor White
Write-Host "   • API: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "📋 Process IDs:" -ForegroundColor Cyan
Write-Host "   • API PID: $($apiProcess.Id)" -ForegroundColor Gray
Write-Host "   • UI PID:  $($uiProcess.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Keep script running until user stops it
while ($true) {
    Start-Sleep -Seconds 10

    # Check if processes are still running
    if ($null -ne $apiProcess -and $apiProcess.HasExited) {
        Write-Host "⚠️  API process stopped. Restarting..." -ForegroundColor Yellow
        Set-Location services/api
        & ".\.venv\Scripts\Activate.ps1"
        $apiProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --reload --port 8000" -PassThru -WindowStyle Minimized
        Set-Location ../..
    }

    if ($null -ne $uiProcess -and $uiProcess.HasExited) {
        Write-Host "⚠️  UI process stopped. Restarting..." -ForegroundColor Yellow
        Set-Location services/ui
        $uiProcess = Start-Process -FilePath "streamlit" -ArgumentList "run app.py --server.port 8501" -PassThru -WindowStyle Minimized
        Set-Location ../..
    }
}
