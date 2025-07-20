@echo off
title Installation OmniParser Officiel
echo ========================================
echo     Installation OmniParser Officiel
echo ========================================
echo.

REM Vérifier si le dossier existe déjà
if exist omniparser_official (
    echo Le dossier omniparser_official existe deja.
    set /p response="Voulez-vous le supprimer et reinstaller ? (y/n): "
    if /i "%response%"=="y" (
        echo Suppression du dossier existant...
        rmdir /s /q omniparser_official
    ) else (
        echo Installation annulee.
        pause
        exit
    )
)

echo.
echo 1. Clonage du repository OmniParser...
git clone https://github.com/microsoft/OmniParser.git omniparser_official
if errorlevel 1 (
    echo Erreur lors du clonage !
    pause
    exit
)

echo.
echo 2. Installation des dependances Python...

REM Créer un environnement virtuel si souhaité
REM python -m venv omniparser_env
REM call omniparser_env\Scripts\activate

REM Installer les dépendances principales
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.45.1
pip install ultralytics
pip install opencv-python
pip install Pillow numpy
pip install easyocr
pip install paddlepaddle paddleocr
pip install supervision matplotlib
pip install fastapi uvicorn python-multipart
pip install gradio
pip install huggingface-hub

echo.
echo 3. Telechargement des modeles...
python download_omniparser_models.py

echo.
echo ========================================
echo Installation terminee !
echo.
echo Pour lancer OmniParser officiel:
echo - Double-cliquez sur start_omniparser_official.bat
echo - Le serveur sera disponible sur http://localhost:8001
echo ========================================
pause