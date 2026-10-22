@echo off
title Godot 4 Editor - 2D Platformer
cd /d "%~dp0godot-4game"

set "GODOT_EXE=%~dp0engine\Godot_v4.3-stable_win64.exe"
if not exist "%GODOT_EXE%" set "GODOT_EXE=%~dp0..\godot engine\Godot_v4.3-stable_win64.exe"

if exist "%GODOT_EXE%" (
    start "" "%GODOT_EXE%" -e
) else (
    echo [ERROR] Godot 4 executable not found!
    echo Checked:
    echo   "%~dp0engine\Godot_v4.3-stable_win64.exe"
    echo   "%~dp0..\godot engine\Godot_v4.3-stable_win64.exe"
    pause
)
