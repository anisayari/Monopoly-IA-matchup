@echo off
cls
title Monopoly IA - Complete System
echo ================================================
echo              MONOPOLY IA SYSTEM
echo ================================================
echo.
echo Starting system initialization...
echo.

:: Run cleanup script if it exists
if exist cleanup_obsolete_files.bat (
    echo [1/7] Cleaning up obsolete files...
    call cleanup_obsolete_files.bat
    echo       [OK]
) else (
    echo [1/7] Cleanup script not found, skipping...
)

:: Clean up any process using port 8000 (with progress)
echo [2/7] Checking port 8000...
set port_cleaned=0
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    set port_cleaned=1
)
if %port_cleaned%==1 (
    echo       [OK] Port 8000 cleaned
) else (
    echo       [OK] Port 8000 available
)

:: Check calibration first
echo [3/7] Checking calibration...
python check_calibration.py >nul 2>&1
if %errorlevel% neq 0 goto ask_calibration
echo       [OK] Valid calibration found
goto check_terminal_mode

:ask_calibration
echo       [!] Calibration missing or invalid
echo.
echo Calibration is required for clicks to work properly.
set /p response=Do you want to run calibration now? (Y/N): 
if /i "%response%"=="Y" goto run_calibration
echo Calibration skipped - Clicks might not work properly
goto check_terminal_mode

:run_calibration
echo.
echo Starting calibration...
python calibration\run_visual_calibration_complete.py
if %errorlevel% neq 0 (
    echo [!] Calibration failed or cancelled
    echo.
    set /p continue_response=Continue anyway? (Y/N): 
    if /i "%continue_response%"=="N" exit /b 1
)

:check_terminal_mode
echo.
echo [4/7] Checking terminal options...

:: Check if Windows Terminal is available
where wt >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Windows Terminal detected!
    echo.
    echo How would you like to start the services?
    echo [1] Integrated mode - All services in one window (recommended)
    echo [2] Classic mode - Separate windows
    echo [3] Minimal mode - Flask only (manual start for other services)
    echo.
    choice /C 123 /M "Your choice"
    if errorlevel 3 goto minimal_mode
    if errorlevel 2 goto classic_mode
    if errorlevel 1 goto integrated_mode
) else (
    echo Windows Terminal not found - using classic mode
    goto classic_mode
)

:integrated_mode
echo.
echo [5/7] Starting services in integrated terminal...
echo.
echo Layout:
echo +------------------+------------------+
echo !      Flask       !    OmniParser    !
echo !      (5000)      !      (8000)      !
echo +------------------+------------------+
echo ! Monitor (Popups) ! AI Chat/Thoughts !
echo +------------------+------------------+
echo !         AI Actions (Context)        !
echo +-------------------------------------+
echo.

:: Get current directory without trailing backslash
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Use omniparser_lite.py which is already working
set OMNIPARSER_CMD=python omniparser_lite.py
if not exist omniparser_lite.py set OMNIPARSER_CMD=python omniparser_server_native.py

:: Windows Terminal with split panes
wt ^
  new-tab --title "Monopoly IA" ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === FLASK SERVER === && python app.py" ^
  ; split-pane -V ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === OMNIPARSER === && timeout /t 5 && %OMNIPARSER_CMD%" ^
  ; split-pane -V ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === DECISION SERVER === && timeout /t 7 && python services\unified_decision_server.py" ^
  ; split-pane -V ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === MONITOR (Popups) === && timeout /t 10 && python monitor_centralized.py" ^
  ; move-focus left ; move-focus left ; move-focus left ; split-pane -H ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === AI CHAT + THOUGHTS === && timeout /t 12 && python ai_chat_server.py" ^
  ; move-focus right ; split-pane -H ^
  cmd /k "cd /d \"%SCRIPT_DIR%\" && echo === AI ACTIONS (Game Context) === && timeout /t 15 && python ai_actions_server.py"

goto open_browser

:classic_mode
echo.
echo [5/7] Starting services in separate windows...

:: Clean up old processes
echo Cleaning up old processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Monopoly*" >nul 2>&1

:: Clean up port 8000 specifically for OmniParser
echo Checking port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process on port 8000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
echo Done.

:: Start Flask
echo.
echo Starting Flask server...
start "Monopoly IA - Flask" cmd /k "cd /d %~dp0 && python app.py"
timeout /t 3 >nul

:: Start OmniParser
echo Starting OmniParser...
if exist omniparser_lite.py (
    start "Monopoly IA - OmniParser" cmd /k "cd /d %~dp0 && python omniparser_lite.py"
) else (
    start "Monopoly IA - OmniParser" cmd /k "cd /d %~dp0 && python omniparser_server_native.py"
)
timeout /t 3 >nul

:: Start Decision Server
echo Starting AI Decision Server...
start "Monopoly IA - Decision Server" cmd /k "cd /d %~dp0 && python services\unified_decision_server.py"
timeout /t 3 >nul

:: Start Monitor
echo Starting Monitor...
start "Monopoly IA - Monitor" cmd /k "cd /d %~dp0 && python monitor_centralized.py"

:: AI Chat terminal
echo Starting AI Chat...
start "Monopoly IA - AI Chat" cmd /k "cd /d %~dp0 && python ai_chat_server.py"

:: AI Actions terminal
echo Starting AI Actions terminal...
start "Monopoly IA - AI Actions" cmd /k "cd /d %~dp0 && echo === AI ACTIONS (Game Context) === && timeout /t 15 && python ai_actions_server.py"

goto open_browser

:minimal_mode
echo.
echo [5/7] Starting minimal mode (Flask only)...
start "Monopoly IA - Flask" cmd /k "cd /d %~dp0 && python app.py"
echo.
echo [i] You can start other services manually from the Admin panel
goto open_browser

:open_browser
echo.
echo [6/7] Opening web interface...
timeout /t 3 >nul
start http://localhost:5000

echo.
echo [7/7] Auto-launch check...

:: Check if user wants auto-launch from a config file
if exist "config\autolaunch.txt" (
    echo [i] Auto-launch enabled
    echo.
    echo Waiting for Flask to be ready...
    timeout /t 5 >nul
    
    :: Launch Dolphin via Flask API
    echo Launching Dolphin automatically...
    curl -s -X POST http://localhost:5000/api/start-dolphin >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Dolphin launched successfully!
    ) else (
        echo [!] Failed to auto-launch Dolphin
    )
) else (
    echo [i] Auto-launch disabled
    echo    To enable: Create file "config\autolaunch.txt"
)

echo.
echo ================================================
echo                SYSTEM READY!
echo ================================================
echo.
echo Services:
echo    - Flask UI: http://localhost:5000
echo    - OmniParser API: http://localhost:8000
echo    - AI Decision API: http://localhost:7000
echo    - Admin Panel: http://localhost:5000/admin
echo    - Monitoring: http://localhost:5000/monitoring
echo.
echo Next steps:
echo    1. Go to http://localhost:5000
echo    2. Click "Start Dolphin" to launch the game
echo    3. The AI will handle popups automatically!
echo.
echo Tips:
echo    - Use Ctrl+C to stop services
echo    - Check Admin panel for system status
echo    - Run calibration if clicks don't work
echo.
echo ================================================
echo.
pause