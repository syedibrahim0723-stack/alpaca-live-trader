@echo off
title News Radar
cd /d "%~dp0"

echo News Radar
echo ----------

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup, then run this file again.
    echo.
    pause
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo Installing / checking dependencies...
.venv\Scripts\python.exe -m pip install -q --upgrade pip
.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Dependency install failed. See the messages above.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo Created .env from .env.example. You can also enter keys on the Sources page.
)

echo.
echo Starting News Radar at http://127.0.0.1:8100
echo Keep this window open. Press Ctrl+C to stop.
echo ----------

:: Open the browser a few seconds after the server starts.
start "" cmd /c "timeout /t 4 >nul && start http://127.0.0.1:8100"

.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8100

echo.
echo Server stopped.
pause
