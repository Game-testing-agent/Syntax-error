@echo off
REM run_agentic_test.bat — Launch the Autonomous Agentic Testing Loop
REM
REM Usage:
REM   run_agentic_test.bat                              (default: auto-launch game window, coverage, budget=20)
REM   run_agentic_test.bat --budget 10 --strategy risk
REM   run_agentic_test.bat --mode waypoints --budget 5
REM
REM All arguments are forwarded to agentic_tester.py.
REM Results are saved to agentic_test_results\<run_id>.json

cd /d "%~dp0"

echo [*] Spawning Live Agent Telemetry Monitor (run_reader.bat)...
if exist "run_reader.bat" (
    start "Game 2 - Live Agent Telemetry Monitor" call run_reader.bat
) else if exist "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" (
    start "Game 2 - Live Agent Telemetry Monitor" "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" log_reader.py
) else (
    start "Game 2 - Live Agent Telemetry Monitor" python log_reader.py
)

python agentic_tester.py --launch %*

echo.
echo ======================================================================
if exist "game_events.jsonl" (
    echo [OK] Game events recorded in: game_events.jsonl
) else (
    echo [INFO] game_events.jsonl will be updated by Godot GameLogger.
)
echo ======================================================================
echo.

pause
