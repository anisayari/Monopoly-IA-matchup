#!/usr/bin/env python3
"""
Vérification des dépendances pour Monopoly Manager
"""

import sys
import subprocess
from importlib import import_module

print("🔍 Vérification des dépendances pour Monopoly Manager")
print("=" * 60)

# Liste des modules requis avec leurs noms d'import et de package pip
REQUIRED_MODULES = [
    # (module_import_name, pip_package_name, description)
    ('flask', 'flask', 'Framework web Flask'),
    ('flask_socketio', 'flask-socketio', 'WebSocket pour Flask'),
    ('socketio', 'python-socketio', 'Client/Server SocketIO'),
    ('redis', 'redis', 'Base de données Redis'),
    ('eventlet', 'eventlet', 'Networking concurrent'),
    ('dolphin_memory_engine', 'dolphin-memory-engine', 'Lecture mémoire Dolphin'),
    ('openai', 'openai', 'API OpenAI pour l\'IA'),
    ('pyautogui', 'pyautogui', 'Automatisation GUI'),
    ('PIL', 'pillow', 'Traitement d\'images'),
    ('pygetwindow', 'pygetwindow', 'Gestion des fenêtres'),
    ('cv2', 'opencv-python', 'Computer Vision'),
    ('mss', 'mss', 'Capture d\'écran'),
    ('win32gui', 'pywin32', 'API Windows'),
    ('requests', 'requests', 'Requêtes HTTP'),
    ('colorama', 'colorama', 'Couleurs terminal'),
    ('dotenv', 'python-dotenv', 'Variables d\'environnement'),
]

missing_modules = []
installed_modules = []

print("\n📋 Vérification des modules:\n")

for module_name, pip_name, description in REQUIRED_MODULES:
    try:
        import_module(module_name)
        print(f"✅ {description:.<40} OK")
        installed_modules.append(module_name)
    except ImportError:
        print(f"❌ {description:.<40} MANQUANT")
        missing_modules.append((module_name, pip_name))

# Résumé
print("\n" + "=" * 60)
print(f"✅ Modules installés: {len(installed_modules)}/{len(REQUIRED_MODULES)}")

if missing_modules:
    print(f"❌ Modules manquants: {len(missing_modules)}")
    print("\n📦 Pour installer les modules manquants, exécutez:")
    print("\n" + "-" * 60)
    
    # Commande d'installation
    pip_packages = [pip_name for _, pip_name in missing_modules]
    install_cmd = f"pip install {' '.join(pip_packages)}"
    print(f"pip install {' '.join(pip_packages)}")
    print("-" * 60)
    
    # Demander si on veut installer maintenant
    response = input("\n🤔 Voulez-vous installer maintenant? (O/n): ").strip().lower()
    if response in ['', 'o', 'oui', 'y', 'yes']:
        print("\n🚀 Installation en cours...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + pip_packages)
            print("\n✅ Installation terminée!")
        except subprocess.CalledProcessError:
            print("\n❌ Erreur lors de l'installation")
            sys.exit(1)
else:
    print("\n✅ Toutes les dépendances sont installées!")
    
    # Vérifier Redis
    print("\n🔍 Vérification de Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("✅ Redis est accessible")
    except:
        print("⚠️  Redis n'est pas accessible (optionnel)")
        print("   Pour l'activer: docker run -d -p 6379:6379 redis:alpine")
    
    # Vérifier la clé API OpenAI
    print("\n🔍 Vérification de l'API OpenAI...")
    import os
    if os.getenv('OPENAI_API_KEY'):
        print("✅ Clé API OpenAI configurée")
    else:
        print("⚠️  Clé API OpenAI non configurée (optionnel)")
        print("   Pour l'activer: set OPENAI_API_KEY=votre-clé")

print("\n" + "=" * 60)
input("\nAppuyez sur Entrée pour fermer...")