@echo off
title Syntax-Error QA Explorer Dashboard
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ======================================================================
echo    SYNTAX-ERROR // QA EXPLORER & BOT CONTROL DASHBOARD
echo ======================================================================
echo.
echo [*] Checking Python runtime...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 was not found in PATH!
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo [*] Verifying dependencies (FastAPI, Uvicorn)...
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required dashboard packages...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo ======================================================================
echo    Starting Dashboard Server on http://localhost:8080
echo    Press Ctrl+C to stop the dashboard server.
echo ======================================================================
echo.

python server.py --port 8080 --open

pause

