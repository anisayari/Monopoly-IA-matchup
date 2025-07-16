@echo off
chcp 65001 >nul
title MonopolyIA - Complete System v3
echo ================================================
echo     MONOPOLY IA - COMPLETE SYSTEM V3
echo ================================================
echo.
echo Initializing system with health checks...
echo.

REM 1. Initial Health Check
echo [PHASE 1] Initial Health Check
echo ================================================
python -c "from services.health_check_service import HealthCheckService; checker = HealthCheckService(); all_healthy, messages = checker.perform_startup_checks(auto_start=False); print('\n'.join(messages))"
echo.

REM 2. Start OmniParser PROPERLY
echo [PHASE 2] Starting Critical Services
echo ================================================
echo.
echo [1/6] Starting OmniParser...
netstat -an | findstr :8000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo   - Launching OmniParser Lite with GPU support...
    start "OmniParser Lite" cmd /k "python omniparser_lite.py"
    echo   - Waiting for OmniParser to initialize...
    timeout /t 8 /nobreak >nul
) else (
    echo   - OmniParser already running on port 8000
)

REM 3. Start Unified Decision Server
echo.
echo [2/6] Starting Unified Decision Server...
netstat -an | findstr :7000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    if exist services\unified_decision_server.py (
        echo   - Launching Unified Decision Server on port 7000...
        start "Unified Decision Server" cmd /k "python services\unified_decision_server.py"
        timeout /t 3 /nobreak >nul
    ) else (
        echo   - [WARNING] Unified Decision Server not found
    )
) else (
    echo   - Unified Decision Server already running on port 7000
)

REM 4. Start AI Actions Terminal
echo.
echo [3/6] Starting AI Actions Terminal...
start "AI Actions Terminal" launch_ai_actions_terminal.bat
timeout /t 2 /nobreak >nul
echo   - AI Actions Terminal started

REM 5. Start Flask Main Server
echo.
echo [4/6] Starting Flask Main Server...
netstat -an | findstr :5000 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo   - Launching Flask server on port 5000...
    start "MonopolyIA Server" cmd /k "python app.py"
    timeout /t 5 /nobreak >nul
) else (
    echo   - Flask server already running on port 5000
)

REM 6. Final Health Check
echo.
echo [5/6] Final Health Check...
echo ================================================
python -c "import requests; import time; time.sleep(2); r = requests.post('http://localhost:5000/api/health/check', json={'auto_start': True}); print('\n'.join(r.json().get('messages', ['Connection error'])))" 2>nul
echo.

REM 7. Start Continuous Monitor (optional)
echo [6/6] Monitor Options
echo ================================================
echo.
echo Monitor services available:
echo   1. monitor_centralized.py - Basic popup detection
echo   2. monitor_continuous.py - Advanced AI monitoring with context
echo.
echo To start advanced monitoring, run: start_monitor_continuous.bat
echo.

REM 8. Open browser
echo [PHASE 3] Opening Web Interface
echo ================================================
timeout /t 2 /nobreak >nul
start http://localhost:5000

echo.
echo ================================================
echo     SYSTEM STARTUP COMPLETE!
echo ================================================
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
echo   [*] Unified Decision Server (Port 7000)
echo   [*] AI Actions Service
echo.
echo Next Steps:
echo   1. Use web interface to start Dolphin
echo   2. Run start_monitor_continuous.bat for AI monitoring
echo   3. Check http://localhost:5000/api/health for status
echo.
echo Commands:
echo   - Health Check: python check_system_health.py
echo   - Stop All: Close this window
echo   - Logs: http://localhost:5000/api/logs
echo.
echo ================================================
echo.
pause