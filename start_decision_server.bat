@echo off
title Monopoly IA - Decision Server (Port 7000)
echo ================================================
echo         STARTING AI DECISION SERVER
echo ================================================
echo.
echo This server handles AI decisions for popups
echo Running on port 7000 with endpoint /api/decide
echo.

:: Start the unified decision server
python services\unified_decision_server.py

pause