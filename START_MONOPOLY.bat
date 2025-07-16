@echo off
cls
title MonopolyIA - Automated System
echo ============================================================
echo                  MONOPOLY IA SYSTEM
echo ============================================================
echo.

REM Clean up old processes
echo Cleaning up old processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq OmniParser*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Flask*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Monitor*" >nul 2>&1
echo Done.
echo.

REM Start OmniParser
echo [1/4] Starting OmniParser (UI Detection)...
if exist omniparser_lite.py (
    start "OmniParser" /min cmd /c "python omniparser_lite.py"
    timeout /t 5 >nul
    echo       OmniParser started on port 8000
) else (
    echo       ERROR: omniparser_lite.py not found!
)

REM Start Flask
echo.
echo [2/4] Starting Main Server...
if exist app.py (
    start "Flask Server" /min cmd /c "python app.py"
    timeout /t 5 >nul
    echo       Flask server started on port 5000
) else (
    echo       ERROR: app.py not found!
)

REM Monitor will be started by Flask automatically when Dolphin is launched
echo.
echo [3/4] Monitor Service...
echo       Monitor will start automatically when Dolphin is launched

REM Open Browser
echo.
echo [4/4] Opening Web Interface...
timeout /t 2 >nul
start http://localhost:5000

REM Final message
echo.
echo ============================================================
echo                    SYSTEM READY!
echo ============================================================
echo.
echo Services Running:
echo   - OmniParser (Port 8000) - Detects UI elements
echo   - Flask Server (Port 5000) - Main application
echo   - Popup Monitor - Watches for game popups
echo.
echo Next Steps:
echo   1. Click "Start Dolphin" in the web interface
echo   2. Load your Monopoly game
echo   3. The AI will handle popups automatically!
echo.
echo To stop: Close this window
echo ============================================================
echo.
pause