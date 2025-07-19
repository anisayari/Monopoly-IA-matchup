"""
Configuration pour l'application Monopoly Manager
"""

import os
import json
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Chemins des fichiers et dossiers
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(WORKSPACE_DIR, "config")
USER_CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")
CONTEXT_DIR = os.path.join(WORKSPACE_DIR, "contexte")
CONTEXT_FILE = os.path.join(CONTEXT_DIR, "game_context.json")
CONTEXT_HISTORY_DIR = os.path.join(CONTEXT_DIR, "history")
PROGRAM_FILES_DIR = os.getenv("ProgramFiles", "C:/Program Files")

# Créer le dossier config s'il n'existe pas
os.makedirs(CONFIG_DIR, exist_ok=True)

# Charger la configuration utilisateur si elle existe
user_config = {}
if os.path.exists(USER_CONFIG_FILE):
    try:
        with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement de la configuration utilisateur: {e}")

# Configuration de Dolphin avec valeurs par défaut ou depuis la config utilisateur
DOLPHIN_PATH = user_config.get('dolphin_path', os.path.join(PROGRAM_FILES_DIR, "Dolphin-x64", "Dolphin.exe"))
DOLPHIN_MEMORY_ENGINE_PATH = user_config.get('memory_engine_path', os.path.join(PROGRAM_FILES_DIR, "dolphin-memory-engine", "DolphinMemoryEngine.exe"))
MONOPOLY_ISO_PATH = user_config.get('monopoly_iso_path', os.path.join(WORKSPACE_DIR, "game_files", "stating_state.rvz"))
SAVE_FILE_PATH = user_config.get('save_file_path', os.path.join(WORKSPACE_DIR, "game_files", "starting_state.sav"))

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
FLASK_HOST = user_config.get('flask_host', "127.0.0.1")
FLASK_PORT = user_config.get('flask_port', 5000)
FLASK_DEBUG = user_config.get('flask_debug', True)

# Intervalle de rafraîchissement du contexte (en millisecondes)
REFRESH_INTERVAL = user_config.get('refresh_interval', 2000)