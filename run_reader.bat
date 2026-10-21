@echo off
title Game 2 - Live Agent Telemetry Monitor
cd /d "%~dp0"
if exist "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" (
    "C:\Users\vinay\AppData\Local\Programs\Python\Python311\python.exe" log_reader.py
) else (
    python log_reader.py
)
pause
