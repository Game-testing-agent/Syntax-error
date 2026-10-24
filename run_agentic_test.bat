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
python agentic_tester.py --launch %*
pause
