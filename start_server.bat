@echo off
title Audio Detector Server
echo =========================================
echo Starting Audio Detector Server...
echo =========================================

:: Navigate to the web directory relative to where this batch file is located
cd /d "%~dp0web"

:: Launch default web browser automatically after 4 seconds
start /b "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000/app"

:: Run the FastAPI server using the virtual environment
"..\lid-pipeline\venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

:: Pause if the server stops or crashes so the user can see the error
pause

