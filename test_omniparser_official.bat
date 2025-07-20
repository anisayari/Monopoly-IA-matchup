@echo off
title Test OmniParser Official API
echo ================================================
echo        TEST OMNIPARSER OFFICIAL API
echo ================================================
echo.
echo Ce script va tester l'API OmniParser Official
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH
    pause
    exit /b 1
)

REM Vérifier si requests est installé
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [AVERTISSEMENT] Le module 'requests' n'est pas installe
    echo Installation en cours...
    pip install requests pillow
)

echo.
echo Options de test:
echo.
echo [1] Test avec image generee automatiquement
echo [2] Test avec votre propre image
echo [3] Test avec capture Monopoly (si disponible)
echo.
choice /C 123 /N /M "Votre choix (1-3): "

if errorlevel 3 goto :capture
if errorlevel 2 goto :custom
if errorlevel 1 goto :auto

:auto
echo.
echo Lancement du test avec image auto-generee...
python test_omniparser_official.py
goto :end

:custom
echo.
set /p IMAGE_PATH="Entrez le chemin complet de votre image: "
python test_omniparser_official.py "%IMAGE_PATH%"
goto :end

:capture
echo.
echo Recherche d'images de capture Monopoly...

REM Chercher dans le dossier capture s'il existe
if exist capture (
    dir /b capture\*.png capture\*.jpg capture\*.jpeg 2>nul
    if not errorlevel 1 (
        echo.
        echo Images trouvees dans le dossier capture.
        set /p CAPTURE_NAME="Entrez le nom du fichier (avec extension): "
        python test_omniparser_official.py "capture\%CAPTURE_NAME%"
        goto :end
    )
)

REM Chercher des screenshots
dir /b screenshot*.png monopoly*.png game*.png 2>nul
if not errorlevel 1 (
    echo.
    echo Screenshots trouves.
    set /p CAPTURE_NAME="Entrez le nom du fichier: "
    python test_omniparser_official.py "%CAPTURE_NAME%"
    goto :end
)

echo.
echo Aucune image de capture trouvee.
echo Utilisation de l'image de test par defaut...
python test_omniparser_official.py
goto :end

:end
echo.
pause