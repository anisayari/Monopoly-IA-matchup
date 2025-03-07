"""
Configuration pour l'application Monopoly Manager
"""

import os

# Chemins des fichiers et dossiers
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTEXT_DIR = os.path.join(WORKSPACE_DIR, "contexte")
CONTEXT_FILE = os.path.join(CONTEXT_DIR, "game_context.json")
CONTEXT_HISTORY_DIR = os.path.join(CONTEXT_DIR, "history")

# Configuration de Dolphin
DOLPHIN_PATH = r"C:\Users\ayari\Downloads\dolphin-2412-x64\Dolphin-x64\Dolphin.exe"
DOLPHIN_MEMORY_ENGINE_PATH = r"C:\Users\ayari\Downloads\dolphin-memory-engine-52d459b-windows-amd64 (1)\DolphinMemoryEngine.exe"
MONOPOLY_ISO_PATH = r"C:\Users\ayari\Downloads\Monopoly Collection (Europe) (En,Fr)\Monopoly Collection (Europe) (En,Fr).rvz"
SAVE_FILE_PATH = os.path.join(WORKSPACE_DIR, "game_files", "starting_state.sav")

# Configuration de l'application Flask
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Intervalle de rafraîchissement du contexte (en millisecondes)
REFRESH_INTERVAL = 2000 