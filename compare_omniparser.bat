@echo off
title Comparaison OmniParser Lite vs Official
echo ================================================
echo     COMPARAISON OMNIPARSER LITE VS OFFICIAL
echo ================================================
echo.
echo Ce script compare les sorties JSON des deux
echo versions d'OmniParser.
echo.
echo PREREQUIS:
echo - OmniParser Lite doit etre demarre sur le port 8000
echo - OmniParser Official doit etre demarre sur le port 8002
echo.
echo Pour demarrer les serveurs:
echo 1. Ouvrez deux terminaux
echo 2. Dans le premier: start_omniparser.bat (choisir option 1)
echo 3. Dans le second: start_omniparser.bat (choisir option 2)
echo.
pause
echo.
echo Lancement de la comparaison...
echo.
python compare_omniparser_outputs.py
pause