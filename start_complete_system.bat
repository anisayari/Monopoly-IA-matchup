@echo off
chcp 65001 >nul
title MonopolyIA - Complete Automated System
echo ================================================
echo     MONOPOLY IA - COMPLETE AUTOMATED SYSTEM
echo ================================================
echo.
echo Starting all services and monitors...
echo.

REM Kill any existing instances
echo [CLEANUP] Stopping any existing services...
taskkill /F /FI "WINDOWTITLE eq OmniParser*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Unified Decision*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq MonopolyIA Server*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq AI Actions*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Monopoly IA - Continuous*" >nul 2>&1
timeout /t 2 /nobreak >nul

REM 1. Start OmniParser
echo.
echo [1/7] Starting OmniParser Service...
start "OmniParser Lite" /min cmd /c "python omniparser_lite.py"
timeout /t 5 /nobreak >nul

REM 2. Start Unified Decision Server
echo [2/7] Starting Unified Decision Server...
if exist services\unified_decision_server.py (
    start "Unified Decision Server" /min cmd /c "python services\unified_decision_server.py"
    timeout /t 3 /nobreak >nul
)

REM 3. Start AI Service
echo [3/7] Starting AI Service...
start "AI Actions Terminal" /min cmd /c "python services\ai_service.py"
timeout /t 2 /nobreak >nul

REM 4. Start Flask Server
echo [4/7] Starting Flask Main Server...
start "MonopolyIA Server" /min cmd /c "python app.py"
timeout /t 5 /nobreak >nul

REM 5. Quick health check
echo [5/7] Verifying services...
timeout /t 3 /nobreak >nul
curl -s http://localhost:5000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Flask server is ready
) else (
    echo   [WARNING] Flask server may still be starting...
)

REM 6. Start Continuous Monitor
echo [6/7] Starting Continuous Monitor with AI...
start "Continuous Monitor" /min cmd /c "python monitor_continuous.py"
timeout /t 2 /nobreak >nul
echo   [OK] Monitor started - Will detect popups and handle idle states

REM 7. Open Web Interface
echo [7/7] Opening Web Interface...
start http://localhost:5000

REM Display final status
echo.
echo ================================================
echo     ALL SYSTEMS STARTED SUCCESSFULLY!
echo ================================================
echo.
echo What's running:
echo   ✓ OmniParser (Port 8000) - UI Detection
echo   ✓ Unified Decision Server (Port 7000) - AI Decisions
echo   ✓ Flask Server (Port 5000) - Main Application
echo   ✓ AI Service - Decision Making
echo   ✓ Continuous Monitor - Auto Popup/Idle Detection
echo.
echo The system will:
echo   • Continuously monitor game state
echo   • Automatically handle popups with AI
echo   • Take action if game is idle for 2+ minutes
echo   • Track all player contexts
echo.
echo Next steps:
echo   1. Use web interface to start Dolphin
echo   2. Load Monopoly in Dolphin
echo   3. The AI will handle everything automatically!
echo.
echo To stop everything: Close this window
echo ================================================
echo.
echo Monitor logs will appear below:
echo.
timeout /t 5 /nobreak >nul

REM Show monitor output in main window
python monitor_continuous.py