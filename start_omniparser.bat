@echo off
title OmniParser Server Launcher
echo ================================================
echo         OMNIPARSER SERVER LAUNCHER
echo ================================================
echo.
echo Choisissez la version d'OmniParser a lancer:
echo.
echo [1] OmniParser Lite (Version custom)
echo [2] OmniParser Official (Microsoft)
echo [3] Quitter
echo.
choice /C 123 /N /M "Votre choix (1-3): "

if errorlevel 3 goto :end
if errorlevel 2 goto :official
if errorlevel 1 goto :lite

:lite
cls
echo ================================================
echo      LANCEMENT OMNIPARSER LITE (CUSTOM)
echo ================================================
echo.
echo Port: 8000
echo Version: Custom optimisee pour Monopoly
echo.
python omniparser_lite.py
goto :end

:official
cls
echo ================================================
echo     LANCEMENT OMNIPARSER OFFICIAL (MICROSOFT)
echo ================================================
echo.

REM Vérifier si l'installation est complète
if not exist omniparser_official (
    echo [ERREUR] OmniParser Official n'est pas installe !
    echo.
    echo Lancez d'abord install_omniparser_official.bat
    echo.
    pause
    goto :end
)

if not exist weights\icon_detect\model.pt (
    echo [AVERTISSEMENT] Les modeles ne sont pas telecharges !
    echo.
    echo Lancez install_omniparser_official.bat pour
    echo telecharger les modeles.
    echo.
    pause
    goto :end
)

echo Port: 8002 (change du port 8001 car conflit avec Omniverse)
echo Version: Implementation officielle Microsoft
echo.
python omniparser_official_api.py
goto :end

:end
pause