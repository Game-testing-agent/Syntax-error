@echo off
title Level 1 Coordinate Recorder - GDQuest 2D Platformer
cd /d "%~dp0"

echo ===============================================================================
echo   Starting Standalone Level 1 Coordinate Recorder
echo   Play manually in Godot. Die and retry as many times as you like.
echo   Type 'over' in this terminal when finished.
echo ===============================================================================

python level1_coordinate_recorder.py
pause
