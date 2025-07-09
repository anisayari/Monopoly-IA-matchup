"""
Configuration pour l'application Monopoly Manager
"""

import os
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Chemins des fichiers et dossiers
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTEXT_DIR = os.path.join(WORKSPACE_DIR, "contexte")
CONTEXT_FILE = os.path.join(CONTEXT_DIR, "game_context.json")
CONTEXT_HISTORY_DIR = os.path.join(CONTEXT_DIR, "history")
PROGRAM_FILES_DIR = os.getenv("ProgramFiles", "C:/Program Files")

# Configuration de Dolphin
DOLPHIN_PATH = os.path.join(PROGRAM_FILES_DIR, "Dolphin-x64", "Dolphin.exe")
DOLPHIN_MEMORY_ENGINE_PATH = os.path.join(PROGRAM_FILES_DIR, "dolphin-memory-engine", "DolphinMemoryEngine.exe")
MONOPOLY_ISO_PATH = os.path.join(WORKSPACE_DIR, "game_files", "stating_state.rvz")
SAVE_FILE_PATH = os.path.join(WORKSPACE_DIR, "game_files", "starting_state.sav")

# Vérification de l'existence des fichiers et dossiers nécessaires
if not os.path.exists(DOLPHIN_PATH):
    print("Dolphin executable not found at the specified path. Please check the installation directory.")
if not os.path.exists(DOLPHIN_MEMORY_ENGINE_PATH):
    print("Dolphin Memory Engine executable not found at the specified path. Please check the installation directory.")
if not os.path.exists(MONOPOLY_ISO_PATH):
    print("Monopoly ISO file not found at the specified path. Please check the game files directory.")
if not os.path.exists(SAVE_FILE_PATH):
    print("Save file not found at the specified path. Please check the game files directory.")

# Configuration de l'application Flask
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Intervalle de rafraîchissement du contexte (en millisecondes)
REFRESH_INTERVAL = 2000