@echo off
REM run_fault_injection.bat — Controlled Fault Injection Tests for AI Game Tester Logger
REM Runs the fault injection test suite headlessly and writes results to console.

setlocal enabledelayedexpansion

echo ====================================================
echo  FAULT INJECTION TEST RUNNER
echo  AI Game Tester Logger - Schema 1.0
echo ====================================================
echo.

set "GODOT="
set "PROJECT=godot-4game"

REM Search for Godot 4 executable
for %%G in (
    "%USERPROFILE%\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"
    "%USERPROFILE%\Downloads\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64.exe"
    ".\engine\Godot_v4.3-stable_win64.exe"
    ".\engine\Godot_v4.4-stable_win64.exe"
    ".\engine\godot.exe"
    "C:\Godot\Godot_v4.3-stable_win64.exe"
    "C:\Program Files\Godot\Godot_v4.3-stable_win64.exe"
) do (
    if exist "%%~G" (
        set "GODOT=%%~G"
        goto :found_godot
    )
)

REM Fallback: search engine directory or Downloads
for %%F in (
    "engine\*.exe"
    "%USERPROFILE%\Downloads\Godot*\Godot*_win64_console.exe"
    "%USERPROFILE%\Downloads\Godot*\Godot*_win64.exe"
) do (
    echo %%~F | find /i "Godot" >nul && (
        set "GODOT=%%~F"
        goto :found_godot
    )
)

echo [ERROR] Godot 4 executable not found.
echo         Place Godot_v4.x-stable_win64.exe in the engine\ folder or in Downloads.
pause
exit /b 1

:found_godot
echo [OK] Using Godot: !GODOT!
echo [OK] Project   : %PROJECT%
echo.
echo Running fault injection test...
echo.

"!GODOT!" --headless --path "%~dp0%PROJECT%" --script res://src/Tests/test_fault_injection.gd

echo.
echo ====================================================
echo  Fault injection tests complete.
echo  Log written to: game_events.jsonl
echo ====================================================
echo.
pause
