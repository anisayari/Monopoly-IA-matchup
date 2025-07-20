@echo off
title OmniParser Official API Server (Port 8001)
echo ================================================
echo         OMNIPARSER OFFICIAL API SERVER
echo ================================================
echo.
echo Ce serveur utilise l'implementation officielle
echo de Microsoft OmniParser
echo.
echo Endpoints:
echo   - GET  http://localhost:8001/         (Status)
echo   - GET  http://localhost:8001/health   (Health check)
echo   - POST http://localhost:8001/parse/   (Parse image)
echo.
echo ================================================
echo.

REM Lancer le serveur
python omniparser_official_api.py

pause