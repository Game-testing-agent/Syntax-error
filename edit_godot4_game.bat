@echo off
title Godot 4 Editor - 2D Platformer
cd /d "%~dp0godot-4game"

set "GODOT_EXE="

for %%F in (
    "%~dp0engine\Godot_v4*.exe"
    "%~dp0engine\godot4*.exe"
    "%~dp0engine\godot.exe"
    "%USERPROFILE%\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64.exe"
    "%USERPROFILE%\Downloads\Godot*\Godot*_win64.exe"
    "%~dp0..\godot engine\Godot_v4*.exe"
    "C:\Program Files\Godot\Godot_v4*.exe"
    "%~dp0engine\*.exe"
) do (
    if not defined GODOT_EXE (
        echo %%~nxF | findstr /i /v "console v3" >nul && if exist "%%~F" set "GODOT_EXE=%%~F"
    )
)

if exist "%GODOT_EXE%" (
    echo [INFO] Found Godot: "%GODOT_EXE%"
    start "" "%GODOT_EXE%" -e --path "%~dp0godot-4game"
) else (
    echo [ERROR] Godot 4 executable not found!
    pause
)
