@echo off
title MonopolyIA - Complete System Launcher
cls
echo ============================================================
echo             MONOPOLY IA - SYSTEM LAUNCHER
echo ============================================================
echo.

REM Kill existing processes
echo [CLEANUP] Stopping any existing services...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq OmniParser*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Flask*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Unified*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Monitor*" >nul 2>&1
timeout /t 2 >nul

REM Start OmniParser
echo.
echo [1/5] Starting OmniParser Service...
start "OmniParser Service" /min cmd /c "python omniparser_lite.py"
echo       Waiting for OmniParser to initialize...
timeout /t 6 >nul

REM Start Unified Decision Server (if exists)
echo.
echo [2/5] Starting AI Decision Server...
if exist services\unified_decision_server.py (
    start "Unified Decision Server" /min cmd /c "python services\unified_decision_server.py"
    echo       AI Decision Server starting...
) else (
    echo       AI Decision Server not found, skipping...
)
timeout /t 3 >nul

REM Start Flask Server
echo.
echo [3/5] Starting Main Application Server...
start "Flask Main Server" /min cmd /c "python app.py"
echo       Flask server starting on port 5000...
timeout /t 5 >nul

REM Start Monitor
echo.
echo [4/5] Starting Game Monitor...
start "Game Monitor" /min cmd /c "python monitor_centralized.py"
echo       Monitor service started...
timeout /t 2 >nul

REM Open Browser
echo.
echo [5/5] Opening Web Interface...
start http://localhost:5000

REM Display Status
echo.
echo ============================================================
echo              SYSTEM STARTUP COMPLETE!
echo ============================================================
echo.
echo Active Services:
echo   * OmniParser ........... Port 8000
echo   * Flask Server ......... Port 5000  
echo   * Game Monitor ......... Active
echo   * AI Decision Server ... Port 7000 (if available)
echo.
echo Instructions:
echo   1. Use the web interface to start Dolphin
echo   2. Load your Monopoly game
echo   3. The AI will automatically handle popups
echo.
echo To stop all services: Close this window
echo ============================================================
echo.
pause