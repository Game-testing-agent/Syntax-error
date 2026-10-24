@echo off
setlocal enabledelayedexpansion
title 2D Platformer - Universal Setup and Launcher
cd /d "%~dp0"

echo ======================================================
echo   2D PLATFORMER - UNIVERSAL SETUP ^& GAME LAUNCHER
echo ======================================================
echo.

set "ENGINE_DIR=%~dp0engine"
set "GODOT_EXE=%ENGINE_DIR%\Godot_v4.3-stable_win64.exe"
set "PROJECT_DIR=%~dp0godot-4game"

:: 1. Check if Godot 4 is installed, download automatically if missing
if not exist "%GODOT_EXE%" (
    echo [*] Godot 4 engine not found.
    echo [*] Downloading Godot 4.3 stable from official release...
    if not exist "%ENGINE_DIR%" mkdir "%ENGINE_DIR%"
    
    set "ZIP_FILE=%ENGINE_DIR%\godot_temp.zip"
    curl.exe -L -o "!ZIP_FILE!" "https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_win64.exe.zip"
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to download Godot 4.
        echo Please check your internet connection and try again.
        pause
        exit /b 1
    )
    
    echo [*] Extracting Godot engine...
    tar.exe -xf "!ZIP_FILE!" -C "%ENGINE_DIR%"
    if exist "!ZIP_FILE!" del "!ZIP_FILE!" >nul 2>&1
    echo [OK] Godot 4 engine installed successfully.
    echo.
) else (
    echo [OK] Godot 4 engine found.
)

:: 2. Pre-import textures and assets on first run if cache is missing
if not exist "%PROJECT_DIR%\.godot\imported" (
    echo [*] First-time setup: compiling game textures and fonts...
    "%GODOT_EXE%" --path "%PROJECT_DIR%" --headless --editor --quit >nul 2>&1
    echo [OK] All assets imported.
    echo.
)

:: 3. Launch the game
echo [*] Starting game...
cd /d "%PROJECT_DIR%"
start "" "%GODOT_EXE%"
echo [OK] Game launched!

:: Close launcher terminal after 3 seconds
timeout /t 3 >nul
exit /b 0
