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
echo   [1] Hybrid Bot: Baseline Mode (Completes Level01 + Level02 reliably)
echo   [2] Hybrid Bot: Controlled Variation Mode (Exploration ^& Bug Hunting)
echo   [3] Target Coordinate Explorer (Navigate directly to X=3117, Y=560)
echo   [W1] Interactive Waypoints Mode (Enter coords one-by-one; pauses at each)
echo   [W2] Sequential Waypoints Mode (Enter N coords at start; waits 3s at each)
echo   [4] Scripted Mode: Basic Platformer (paths/basic_platformer.json)
echo   [5] Scripted Mode: Coin ^& Jump Test (paths/coin_and_jump.json)
echo   [6] Random Exploration Mode (Seed 42, 100 actions)
echo   [7] Coverage-Guided Exploration Mode (150 actions)
echo   [8] Run Hybrid Bot ^& Explorer Test Suite (Validation Tests)
echo   [9] Launch Godot Game Only
echo   [R] Run Telemetry Reader Only (run_reader.bat)
echo   [L] Open Live Color Log Viewer (view_structured_logs.py)
echo   [0] Exit
echo.
echo ======================================================================
set /p CHOICE="Enter your choice [default=1]: "
if "%CHOICE%"=="" set CHOICE=1

if /i "%CHOICE%"=="0" goto :exit
if /i "%CHOICE%"=="1" goto :hybrid_baseline
if /i "%CHOICE%"=="2" goto :hybrid_variation
if /i "%CHOICE%"=="3" goto :target_coord
if /i "%CHOICE%"=="T" goto :target_coord
if /i "%CHOICE%"=="W1" goto :waypoints_interactive
if /i "%CHOICE%"=="10" goto :waypoints_interactive
if /i "%CHOICE%"=="W2" goto :waypoints_sequential
if /i "%CHOICE%"=="11" goto :waypoints_sequential
if /i "%CHOICE%"=="4" goto :scripted_basic
if /i "%CHOICE%"=="5" goto :scripted_coin
if /i "%CHOICE%"=="6" goto :random
if /i "%CHOICE%"=="7" goto :coverage
if /i "%CHOICE%"=="8" goto :tests
if /i "%CHOICE%"=="9" goto :launch_game
if /i "%CHOICE%"=="R" goto :reader_only
if /i "%CHOICE%"=="L" goto :view_logs

echo [ERROR] Invalid choice. Defaulting to Hybrid Baseline Mode...
goto :hybrid_baseline

:start_reader
:: Merged from run_reader.bat - launches telemetry monitor side-by-side
echo [*] Spawning Live Agent Telemetry Monitor (run_reader.bat)...
if exist "run_reader.bat" (
    start "Game 2 - Live Agent Telemetry Monitor" call run_reader.bat
) else if exist "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" (
    start "Game 2 - Live Agent Telemetry Monitor" "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" log_reader.py
) else (
    start "Game 2 - Live Agent Telemetry Monitor" python log_reader.py
)
exit /b 0

:waypoints_interactive
echo.
echo ======================================================================
echo Running Interactive Waypoints Explorer (Mode 1) ...
echo ======================================================================
call :start_reader
python explorer.py --mode waypoints_interactive --launch
goto :end

:waypoints_sequential
echo.
echo ======================================================================
echo Running Sequential Waypoints Explorer (Mode 2) ...
echo ======================================================================
call :start_reader
python explorer.py --mode waypoints_sequential --launch
goto :end

:target_coord
echo.
echo ======================================================================
echo Running Target Coordinate Explorer (X=3117, Y=560) ...
echo ======================================================================
call :start_reader
python explorer.py --mode target_coord --target-coord 3117 560 --launch
goto :end

:hybrid_baseline
echo.
echo Running Hybrid Bot Baseline Mode (Full Level01 + Level02 Route) ...
call :start_reader
python explorer.py --mode hybrid --routes level_routes.json --max-actions 350 --launch
goto :end

:hybrid_variation
echo.
echo Running Hybrid Bot Variation Mode (Seeded Exploratory Variations) ...
call :start_reader
python explorer.py --mode hybrid_variation --seed 42 --routes level_routes.json --max-actions 350 --launch
goto :end

:scripted_basic
echo.
echo Running Scripted Path: paths/basic_platformer.json ...
call :start_reader
python explorer.py --mode scripted --path paths/basic_platformer.json --launch
goto :end

:scripted_coin
echo.
echo Running Scripted Path: paths/coin_and_jump.json ...
call :start_reader
python explorer.py --mode scripted --path paths/coin_and_jump.json --launch
goto :end

:random
echo.
echo Running Random Exploration (seed=42, max-actions=100) ...
call :start_reader
python explorer.py --mode random --seed 42 --max-actions 100 --launch
goto :end

:coverage
echo.
echo Running Coverage-Guided Exploration (max_actions=150) ...
call :start_reader
python explorer.py --mode coverage_guided --max-actions 150 --launch
goto :end

:tests
echo.
echo Running Hybrid Bot & Explorer Test Suite ...
python test_hybrid_bot.py
python test_explorer.py
goto :end

:launch_game
echo.
echo Launching Godot Platformer ...
call run_game.bat
goto :end

:reader_only
echo.
echo Starting Telemetry Monitor Only ...
call run_reader.bat
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
if exist "game_events.jsonl" (
    echo [OK] Game events recorded in: game_events.jsonl
) else (
    echo [INFO] game_events.jsonl will be updated by Godot GameLogger.
)
echo ======================================================================
echo.
pause

:exit
