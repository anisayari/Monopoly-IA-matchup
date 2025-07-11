@echo off
REM Monopoly AI - Windows Launcher
REM This script launches the Monopoly AI system on Windows

echo ========================================
echo  Monopoly AI - Windows Launcher
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3 and add it to PATH
    pause
    exit /b 1
)

echo Python found: 
python --version

REM Check if running from correct directory
if not exist "main.py" (
    echo ERROR: Please run this script from the Monopoly-IA-matchup directory
    pause
    exit /b 1
)

REM Launch the Python launcher
echo.
echo Starting Monopoly AI Launcher...
echo.

python launcher.py

pause