@echo off
title Hybrid Bot - Map 3: Sky Castle (Target: 14638, 800)
cd /d "%~dp0"

echo ======================================================================
echo    HYBRID BOT - MAP 3 (SKY CASTLE)
echo    Destination: X=14638, Y=800
echo ======================================================================
echo.

python run_map.py --map 3 --bot --target-coord 14638 800 --max-actions 600

echo.
echo ======================================================================
echo Hybrid Bot run on Map 3 finished.
echo ======================================================================
echo.
pause
