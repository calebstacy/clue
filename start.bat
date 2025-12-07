@echo off
cd /d "%~dp0"
echo Starting LocalCluely with Electron UI...
echo.

REM Kill any old Python processes first
echo Cleaning up old processes...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 1 /nobreak > nul

REM Start Python backend in a new window
echo Starting Python backend...
start "LocalCluely Backend" cmd /k "venv\Scripts\python.exe main_electron.py"

REM Wait 10 seconds for backend to fully initialize (Whisper loading takes time)
echo Waiting for backend to initialize (this takes ~10 seconds)...
timeout /t 10 /nobreak > nul

REM Start Electron UI
cd electron-ui
echo Starting Electron UI...
call npx electron .

REM When Electron closes, close everything
taskkill /F /FI "WINDOWTITLE eq LocalCluely Backend*" > nul 2>&1
