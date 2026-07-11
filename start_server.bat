@echo off
title Audio Detector Server
echo =========================================
echo Starting Audio Detector Server...
echo =========================================

:: Navigate to the web directory relative to where this batch file is located
cd /d "%~dp0web"

:: Run the FastAPI server using the virtual environment
"..\lid-pipeline\venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

:: Pause if the server stops or crashes so the user can see the error
pause
