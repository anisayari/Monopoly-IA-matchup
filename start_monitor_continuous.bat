@echo off
title Monopoly IA - Continuous Monitor
echo ================================================
echo     MONOPOLY IA - CONTINUOUS MONITOR
echo ================================================
echo.
echo This monitor will:
echo   - Continuously read game state from RAM
echo   - Detect popups automatically
echo   - Ask AI for decisions
echo   - Build game context
echo.
echo Make sure Dolphin is running with Monopoly loaded!
echo.
echo ================================================
echo.
python monitor_continuous.py
pause