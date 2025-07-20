@echo off
title Installation OmniParser Officiel
echo ================================================
echo     INSTALLATION OMNIPARSER OFFICIEL
echo ================================================
echo.

REM Vérifier si git est installé
where git >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe !
    echo Veuillez installer Git depuis https://git-scm.com/
    pause
    exit /b 1
)

REM Vérifier si le dossier existe déjà
if exist omniparser_official (
    echo [INFO] Le dossier omniparser_official existe deja.
    choice /C YN /M "Voulez-vous le supprimer et reinstaller"
    if errorlevel 2 goto :skip_install
    if errorlevel 1 (
        echo [INFO] Suppression du dossier existant...
        rmdir /s /q omniparser_official
    )
)

echo.
echo [1/4] Clonage du repository Microsoft OmniParser...
git clone https://github.com/microsoft/OmniParser.git omniparser_official
if errorlevel 1 (
    echo [ERREUR] Echec du clonage !
    pause
    exit /b 1
)

echo.
echo [2/4] Installation des dependances Python...
echo.

REM Installer les dépendances essentielles
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.45.1
pip install ultralytics
pip install opencv-python
pip install easyocr
pip install fastapi uvicorn
pip install huggingface-hub

echo.
echo [3/4] Creation du dossier weights...
if not exist weights mkdir weights
if not exist weights\icon_detect mkdir weights\icon_detect
if not exist weights\icon_caption_florence mkdir weights\icon_caption_florence

echo.
echo [4/4] Telechargement des modeles OmniParser...
echo.
echo Telechargement du modele de detection d'icones...
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='microsoft/OmniParser', filename='icon_detect/model.pt', local_dir='weights')"

echo.
echo Telechargement de Florence-2 pour les captions...
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='microsoft/Florence-2-base', local_dir='weights/icon_caption_florence')"

:skip_install
echo.
echo ================================================
echo     INSTALLATION TERMINEE !
echo ================================================
echo.
echo Les modeles sont dans le dossier 'weights'
echo Le code source est dans 'omniparser_official'
echo.
echo Utilisez start_omniparser.bat pour lancer
echo le serveur avec l'option de votre choix.
echo ================================================
echo.
pause