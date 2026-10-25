@echo off
title Godot 2D Platformer - RL Training Demonstration
cd /d "%~dp0"

echo ======================================================================
echo    GODOT 2D PLATFORMER - REINFORCEMENT LEARNING DEMONSTRATION
echo    Subsystem: rl_training (Q-Learning Navigation & Stomp Policy)
echo ======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 was not found in PATH!
    pause
    exit /b 1
)

echo [*] Starting Q-Learning training loop (300 episodes)...
echo.
python train.py --episodes 300

echo.
echo ======================================================================
echo    Training demonstration finished!
echo    Artifacts generated:
echo      - rl_training\q_table.json
echo      - rl_training\training_metrics.csv
echo ======================================================================
echo.
pause
