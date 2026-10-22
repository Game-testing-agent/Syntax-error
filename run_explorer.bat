@echo off
title AI Game Tester Explorer - GDQuest 2D Platformer
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ======================================================================
echo    AI GAME TESTER AGENT - EXPLORER CONTROL HUB
echo ======================================================================
echo.
echo Select an exploration mode to run:
echo.
echo   [1] Scripted Mode: Basic Platformer (paths/basic_platformer.json)
echo   [2] Scripted Mode: Coin ^& Jump Test (paths/coin_and_jump.json)
echo   [3] Scripted Mode: Checkpoint Demo (paths/checkpoint_demo.json)
echo   [4] Random Exploration Mode (Seed 42, 100 actions)
echo   [5] Coverage-Guided Exploration Mode (150 actions)
echo   [6] Run Explorer Test Suite (Validation Tests)
echo   [7] Launch Godot Game Only
echo   [8] Open Live Color Log Viewer
echo   [0] Exit
echo.
echo ======================================================================
set /p CHOICE="Enter your choice (0-8) [default=1]: "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="0" goto :exit
if "%CHOICE%"=="1" goto :scripted_basic
if "%CHOICE%"=="2" goto :scripted_coin
if "%CHOICE%"=="3" goto :scripted_checkpoint
if "%CHOICE%"=="4" goto :random
if "%CHOICE%"=="5" goto :coverage
if "%CHOICE%"=="6" goto :tests
if "%CHOICE%"=="7" goto :launch_game
if "%CHOICE%"=="8" goto :view_logs

echo [ERROR] Invalid choice. Defaulting to Scripted Mode...
goto :scripted_basic

:scripted_basic
echo.
echo Running Scripted Path: paths/basic_platformer.json ...
python explorer.py --mode scripted --path paths/basic_platformer.json --launch
goto :end

:scripted_coin
echo.
echo Running Scripted Path: paths/coin_and_jump.json ...
python explorer.py --mode scripted --path paths/coin_and_jump.json --launch
goto :end

:scripted_checkpoint
echo.
echo Running Scripted Path: paths/checkpoint_demo.json ...
python explorer.py --mode scripted --path paths/checkpoint_demo.json --launch
goto :end

:random
echo.
echo Running Random Exploration (seed=42, max_actions=100) ...
python explorer.py --mode random --seed 42 --max-actions 100 --launch
goto :end

:coverage
echo.
echo Running Coverage-Guided Exploration (max_actions=150) ...
python explorer.py --mode coverage_guided --max-actions 150 --launch
goto :end

:tests
echo.
echo Running Explorer Test Suite ...
python test_explorer.py
goto :end

:launch_game
echo.
echo Launching Godot Platformer ...
call run_game.bat
goto :end

:view_logs
echo.
echo Starting Live Structured Log Viewer ...
start "" python view_structured_logs.py game_events.jsonl
goto :end

:end
echo.
echo ======================================================================
echo Explorer task finished.
echo ======================================================================
echo.
pause

:exit
