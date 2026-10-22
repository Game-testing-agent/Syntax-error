@echo off
title AI Game Tester Agent - Structured JSON Log Viewer (Schema 1.0)
cd /d "%~dp0"
if exist "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" (
    "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" view_structured_logs.py
) else (
    python view_structured_logs.py
)
pause
