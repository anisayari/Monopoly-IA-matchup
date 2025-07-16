@echo off
title MonopolyIA - Complete System Startup
echo ================================================
echo     MONOPOLY IA - COMPLETE SYSTEM V3
echo ================================================
echo.
echo Starting all services with proper checks...
echo.

REM Check Python
echo [CHECK] Verifying Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)
echo [OK] Python is available

REM 1. Start OmniParser
echo.
echo [1/6] Starting OmniParser Service...
tasklist /FI "WINDOWTITLE eq OmniParser*" 2>nul | find /I "cmd.exe" >nul
if %errorlevel% neq 0 (
    echo   - Launching OmniParser Lite on port 8000...
    start "OmniParser Lite" /min cmd /k "python omniparser_lite.py"
    timeout /t 5 /nobreak >nul
) else (
    echo   - OmniParser already running
)

REM 2. Start Unified Decision Server
echo.
echo [2/6] Starting Unified Decision Server...
tasklist /FI "WINDOWTITLE eq Unified Decision Server*" 2>nul | find /I "python.exe" >nul
if %errorlevel% neq 0 (
    if exist services\unified_decision_server.py (
        echo   - Launching Unified Decision Server on port 7000...
        start "Unified Decision Server" /min cmd /k "python services\unified_decision_server.py"
        timeout /t 3 /nobreak >nul
    ) else (
        echo   - [WARNING] Unified Decision Server not found, skipping...
    )
) else (
    echo   - Unified Decision Server already running
)

REM 3. Start Flask Main Server
echo.
echo [3/6] Starting Flask Main Server...
tasklist /FI "WINDOWTITLE eq MonopolyIA Server*" 2>nul | find /I "python.exe" >nul
if %errorlevel% neq 0 (
    echo   - Launching Flask server on port 5000...
    start "MonopolyIA Server" /min cmd /k "python app.py"
    timeout /t 5 /nobreak >nul
) else (
    echo   - Flask server already running
)

REM 4. Verify services are responding
echo.
echo [4/6] Verifying services...
timeout /t 3 /nobreak >nul

REM Check Flask
curl -s http://localhost:5000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Flask server is responding
) else (
    echo   [WARNING] Flask server not responding yet
)

REM Check OmniParser
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] OmniParser is responding
) else (
    echo   [WARNING] OmniParser not responding yet
)

REM 5. Start Monitoring Services (wait for user input)
echo.
echo [5/6] Monitoring Services
echo   - Popup Monitor will start after Dolphin is launched
echo   - Use the web interface to start Dolphin first
echo.

REM 6. Start AI Actions Terminal
echo [6/6] Starting AI Actions Terminal...
if exist launch_ai_actions_terminal.bat (
    start "AI Actions Terminal" launch_ai_actions_terminal.bat
) else (
    echo   - [WARNING] AI Actions Terminal not found
)

REM Open browser
echo.
echo ================================================
echo     SYSTEM STARTUP COMPLETE!
echo ================================================
timeout /t 2 /nobreak >nul
start http://localhost:5000

echo.
echo Available interfaces:
echo   - Main Dashboard:         http://localhost:5000
echo   - Monitoring Panel:       http://localhost:5000/monitoring
echo   - Admin Panel:           http://localhost:5000/admin
echo   - OmniParser API:        http://localhost:8000
echo   - Unified Decision API:  http://localhost:7000
echo   - Health Status:         http://localhost:5000/api/health
echo.
echo Active Services:
echo   [*] Flask Server (Port 5000)
echo   [*] OmniParser (Port 8000)
echo   [*] Unified Decision Server (Port 7000) - if available
echo   [*] AI Actions Terminal
echo.
echo Next Steps:
echo   1. Use the web interface to start Dolphin
echo   2. The popup monitor will start automatically when Dolphin is ready
echo   3. Check http://localhost:5000/api/health for system status
echo.
echo Press Ctrl+C to stop all services
echo ================================================
echo.
pause