@echo off
REM PR Review Agent - Startup Script (Windows)
REM This script sets up and starts both the API and UI services

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║      PR Review Agent - Startup Script (Windows)               ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% detected
echo.

REM Setup API service
echo 🔧 Setting up API service...
cd services\api

if not exist ".venv" (
    echo   Creating virtual environment...
    python -m venv .venv
)

echo   Activating virtual environment...
call .venv\Scripts\activate.bat

echo   Installing dependencies...
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist ".env" (
    echo   Creating .env from .env.example...
    copy .env.example .env >nul
    echo   ⚠️  Edit services\api\.env with your API keys!
)

cd ..\..
echo ✅ API service ready!
echo.

REM Setup UI service
echo 🎨 Setting up UI service...
cd services\ui

echo   Installing dependencies...
pip install -q -r requirements.txt

cd ..\..
echo ✅ UI service ready!
echo.

REM Summary
echo ╔════════════════════════════════════════════════════════════════╗
echo ║              Setup Complete! Ready to Launch                   ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🚀 To start the services, open two Command Prompt windows:
echo.
echo   Window 1 (API):
echo     cd services\api
echo     .venv\Scripts\activate.bat
echo     uvicorn app.main:app --reload --port 8000
echo.
echo   Window 2 (UI):
echo     cd services\ui
echo     streamlit run app.py
echo.
echo 📍 Then visit: http://localhost:8501
echo.
pause
