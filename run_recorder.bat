@echo off
title Manual Gameplay Recorder - GDQuest 2D Platformer
cd /d "%~dp0"

set "LEVEL=%1"
if "%LEVEL%"=="" set "LEVEL=1"

echo ===============================================================================
echo   Starting Manual Gameplay Recording for Level %LEVEL%
echo   Controls: Move (A/D or Arrows), Jump (Space / W), Pause (P)
echo   On death, auto-recovery resets the attempt safely.
echo ===============================================================================

python explorer.py --mode record --level %LEVEL% --launch
pause
