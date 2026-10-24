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
echo   [W2] Sequential Waypoints Mode (Enter N coords at start; waits 3s at each)
echo   [1] Complete Hybrid Game Bot (Completes Level01 + Level02 reliably)
echo   [2] Bot Random Explorer (Exploration ^& Bug Hunting)
echo   [4] Trained Path (paths/basic_platformer.json)
echo   [6] Random Explorer (Seed 42, 100 actions)
echo   [9] Launch Godot Game Only
echo   [R] Run Telemetry Reader Only (run_reader.bat)
echo   [L] Open Live Color Log Viewer (view_structured_logs.py)
echo   [0] Exit
echo.
echo ======================================================================
set /p CHOICE="Enter your choice [default=W2]: "
if "%CHOICE%"=="" set CHOICE=W2

if /i "%CHOICE%"=="0" goto :exit
if /i "%CHOICE%"=="W2" goto :waypoints_sequential
if /i "%CHOICE%"=="11" goto :waypoints_sequential
if /i "%CHOICE%"=="1" goto :hybrid_baseline
if /i "%CHOICE%"=="2" goto :hybrid_variation
if /i "%CHOICE%"=="4" goto :scripted_basic
if /i "%CHOICE%"=="6" goto :random
if /i "%CHOICE%"=="9" goto :launch_game
if /i "%CHOICE%"=="R" goto :reader_only
if /i "%CHOICE%"=="L" goto :view_logs

echo [ERROR] Invalid choice. Defaulting to Sequential Waypoints Mode...
goto :waypoints_sequential

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
echo Running Complete Hybrid Game Bot (Full Level01 + Level02 Route) ...
call :start_reader
python explorer.py --mode hybrid --routes level_routes.json --max-actions 350 --launch
goto :end

:hybrid_variation
echo.
echo Running Bot Random Explorer (Seeded Exploratory Variations) ...
call :start_reader
python explorer.py --mode hybrid_variation --seed 42 --routes level_routes.json --max-actions 350 --launch
goto :end

:scripted_basic
echo.
echo Running Trained Path: paths/basic_platformer.json ...
call :start_reader
python explorer.py --mode scripted --path paths/basic_platformer.json --launch
goto :end

:scripted_coin
echo.
echo Running Trained Path: paths/coin_and_jump.json ...
call :start_reader
python explorer.py --mode scripted --path paths/coin_and_jump.json --launch
goto :end

:random
echo.
echo Running Random Explorer (seed=42, max-actions=100) ...
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
