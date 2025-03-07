"""
Application Flask pour Monopoly Manager
"""

import os
import json
import subprocess
import threading
import time
import sys
import importlib.util
from flask import Flask, render_template, jsonify, request, send_from_directory
import config
from src.game.monopoly import MonopolyGame
from src.game.contexte import Contexte
from src.game.listeners import MonopolyListeners
from src.core.game_loader import GameLoader

app = Flask(__name__)

# Variables globales pour le jeu
game = None
contexte = None
dolphin_process = None
terminal_output = []
terminal_lock = threading.Lock()

def initialize_game():
    """Initialise le jeu Monopoly et le contexte en utilisant le code existant dans main.py"""
    global game, contexte
    
    try:
        # Charger le module main.py dynamiquement
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)
        sys.modules["main"] = main_module
        spec.loader.exec_module(main_module)
        
        # Initialiser le GameLoader avec les fichiers manifeste et de sauvegarde
        manifest_path = os.path.join(config.WORKSPACE_DIR, "game_files", "starting_state.jsonc")
        save_path = config.SAVE_FILE_PATH
        
        # Vérifier que les fichiers existent
        if not os.path.exists(manifest_path):
            print(f"Erreur: Le fichier manifeste {manifest_path} n'existe pas")
            return None, None
        
        if not os.path.exists(save_path):
            print(f"Erreur: Le fichier de sauvegarde {save_path} n'existe pas")
            return None, None
        
        # Créer le GameLoader
        data = GameLoader(manifest_path, save_path)
        
        # Créer une instance du jeu
        game = MonopolyGame(data)
        
        # Créer les listeners
        events = MonopolyListeners(game)
        events.tps = 30
        events.interval_player = .1
        
        # Enregistrer les callbacks depuis main.py
        events.on("player_added", main_module.on_player_added)
        events.on("player_removed", main_module.on_player_removed)
        events.on("player_money_changed", main_module.on_player_money_changed)
        events.on("player_name_changed", main_module.on_player_name_changed)
        events.on("player_dice_changed", main_module.on_player_dice_changed)
        events.on("player_goto_changed", main_module.on_player_goto_changed)
        events.on("message_added", main_module.on_message_added)
        events.on("message_removed", main_module.on_message_removed)
        events.on("*", main_module.on_event)
        
        # Initialiser le contexte
        contexte = Contexte(game, events)
        print("📊 Contexte initialisé et prêt à enregistrer les événements")
        
        # Démarrer les listeners pour capturer les événements
        events.start()
        
        return game, contexte
    except Exception as e:
        print(f"Erreur lors de l'initialisation du jeu: {e}")
        import traceback
        traceback.print_exc()
        # Créer des objets vides pour éviter les erreurs
        game = None
        contexte = None
        return None, None

def capture_terminal_output():
    """Capture la sortie du terminal dans une liste circulaire"""
    global terminal_output
    
    # Rediriger stdout vers notre buffer
    original_stdout = sys.stdout
    
    class StdoutRedirector:
        def write(self, text):
            global terminal_output
            if text.strip():  # Ignorer les lignes vides
                with terminal_lock:
                    # Stocker le texte brut avec les emojis
                    terminal_output.append(text.strip())
                    # Garder seulement les 100 dernières lignes
                    if len(terminal_output) > 100:
                        terminal_output = terminal_output[-100:]
            original_stdout.write(text)
        
        def flush(self):
            original_stdout.flush()
    
    sys.stdout = StdoutRedirector()
    
    while True:
        # Capturer la sortie du processus Dolphin
        if dolphin_process:
            try:
                output = dolphin_process.stdout.readline()
                if output and output.strip():  # Ignorer les lignes vides
                    with terminal_lock:
                        terminal_output.append(output.strip())
                        # Garder seulement les 100 dernières lignes
                        if len(terminal_output) > 100:
                            terminal_output = terminal_output[-100:]
            except:
                pass
        time.sleep(0.1)

def cleanup_existing_processes():
    """Nettoie les processus Dolphin et Memory Engine existants"""
    try:
        # Tuer tous les processus Dolphin.exe
        subprocess.run(['taskkill', '/F', '/IM', 'Dolphin.exe'], 
                     creationflags=subprocess.CREATE_NO_WINDOW,
                     stderr=subprocess.PIPE,
                     stdout=subprocess.PIPE)
    except:
        pass  # Ignorer si aucun processus Dolphin n'est en cours
        
    try:
        # Tuer tous les processus DolphinMemoryEngine.exe
        subprocess.run(['taskkill', '/F', '/IM', 'DolphinMemoryEngine.exe'], 
                     creationflags=subprocess.CREATE_NO_WINDOW,
                     stderr=subprocess.PIPE,
                     stdout=subprocess.PIPE)
    except:
        pass  # Ignorer si aucun processus Memory Engine n'est en cours

# Routes Flask
@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', refresh_interval=config.REFRESH_INTERVAL)

@app.route('/static/<path:path>')
def send_static(path):
    """Sert les fichiers statiques"""
    return send_from_directory('static', path)

@app.route('/api/context')
def get_context():
    """Renvoie le contexte actuel du jeu"""
    try:
        # Si Dolphin n'est pas en cours d'exécution, renvoyer un contexte initial
        if not dolphin_process or dolphin_process.poll() is not None:
            return jsonify({
                "global": {
                    "status": "stopped",
                    "message": "Dolphin n'est pas en cours d'exécution",
                    "properties": [],
                    "current_turn": 0,
                    "player_count": 0,
                    "player_names": []
                },
                "events": [],
                "players": {},
                "board": {
                    "spaces": []
                }
            })
            
        # Si le jeu n'est pas initialisé, renvoyer un contexte d'attente
        if not game or not contexte:
            return jsonify({
                "global": {
                    "status": "starting",
                    "message": "Le jeu est en cours d'initialisation",
                    "properties": [],
                    "current_turn": 0,
                    "player_count": 0,
                    "player_names": []
                },
                "events": [],
                "players": {},
                "board": {
                    "spaces": []
                }
            })
            
        if os.path.exists(config.CONTEXT_FILE):
            with open(config.CONTEXT_FILE, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
                context_data["global"]["status"] = "running"
                context_data["global"]["message"] = "Le jeu est en cours d'exécution"
                return jsonify(context_data)
        else:
            return jsonify({
                "global": {
                    "status": "error",
                    "message": "Le fichier de contexte n'existe pas encore",
                    "properties": [],
                    "current_turn": 0,
                    "player_count": 0,
                    "player_names": []
                },
                "events": [],
                "players": {},
                "board": {
                    "spaces": []
                }
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/terminal')
def get_terminal():
    """Renvoie les dernières lignes de sortie du terminal"""
    with terminal_lock:
        return jsonify(terminal_output)

@app.route('/api/players', methods=['GET', 'POST'])
def manage_players():
    """Gère les informations des joueurs"""
    global game
    
    # Vérifier si Dolphin est en cours d'exécution
    if not dolphin_process or dolphin_process.poll() is not None:
        return jsonify({"error": "Dolphin n'est pas en cours d'exécution"}), 503
        
    # Vérifier si le jeu est initialisé
    if not game:
        return jsonify({"error": "Le jeu n'est pas initialisé"}), 503
    
    if request.method == 'GET':
        try:
            players = []
            for p in game.players:
                players.append({
                    'id': p.id,
                    'name': p.name,
                    'money': p.money,
                    'position': p.position
                })
            return jsonify(players)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            data = request.json
            player_id = data.get('id')
            new_name = data.get('name')
            new_money = data.get('money')
            
            # Mettre à jour le joueur
            for p in game.players:
                if p.id == player_id:
                    if new_name:
                        p.name = new_name
                    if new_money is not None:
                        p.money = int(new_money)
            
            # Mettre à jour le contexte
            if contexte is not None:
                contexte._update_context()
                contexte._save_context()
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/dolphin', methods=['POST', 'DELETE'])
def manage_dolphin():
    """Gère le démarrage et l'arrêt de Dolphin"""
    global dolphin_process, game, contexte
    
    if request.method == 'POST':
        try:
            print("Démarrage de Dolphin...")
            
            # Nettoyer les processus existants
            print("Nettoyage des processus existants...")
            cleanup_existing_processes()
            
            # Vérifier que les fichiers existent
            print(f"Vérification des chemins...")
            if not os.path.exists(config.DOLPHIN_PATH):
                return jsonify({"error": f"Dolphin.exe introuvable: {config.DOLPHIN_PATH}"}), 500
                
            if not os.path.exists(config.MONOPOLY_ISO_PATH):
                return jsonify({"error": f"Fichier ISO introuvable: {config.MONOPOLY_ISO_PATH}"}), 500
            
            # Démarrer Dolphin avec le jeu et la sauvegarde
            print(f"Lancement de Dolphin: {config.DOLPHIN_PATH}")
            try:
                # Vérifier que le fichier de sauvegarde existe
                if not os.path.exists(config.SAVE_FILE_PATH):
                    print(f"ATTENTION: Fichier de sauvegarde introuvable: {config.SAVE_FILE_PATH}")
                
                # Lancement de Dolphin avec la sauvegarde
                # Note: Dolphin utilise différents paramètres selon les versions
                # -s : pour charger un état de sauvegarde (state)
                # -l : pour charger un fichier de sauvegarde (load)
                dolphin_cmd = [
                    config.DOLPHIN_PATH,
                    '-b',  # Démarrer en mode batch
                    '-e', config.MONOPOLY_ISO_PATH,
                    '-s', config.SAVE_FILE_PATH  # Utiliser -s pour charger un état de sauvegarde
                ]
                
                print(f"Commande: {' '.join(dolphin_cmd)}")
                dolphin_process = subprocess.Popen(
                    dolphin_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                print(f"Dolphin démarré avec PID: {dolphin_process.pid}")
            except Exception as e:
                print(f"Erreur lors du lancement de Dolphin: {str(e)}")
                return jsonify({"error": f"Erreur lors du lancement de Dolphin: {str(e)}"}), 500
            
            # Attendre un peu que Dolphin démarre
            print("Attente du démarrage de Dolphin...")
            time.sleep(3)
            
            # Lancer Dolphin Memory Engine
            if os.path.exists(config.DOLPHIN_MEMORY_ENGINE_PATH):
                print(f"Lancement de Dolphin Memory Engine: {config.DOLPHIN_MEMORY_ENGINE_PATH}")
                try:
                    # Lancement simplifié de DME
                    dme_cmd = [config.DOLPHIN_MEMORY_ENGINE_PATH]
                    
                    print(f"Commande: {' '.join(dme_cmd)}")
                    if sys.platform == 'win32':
                        dme_process = subprocess.Popen(
                            dme_cmd,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        dme_process = subprocess.Popen(
                            dme_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    
                    print(f"Dolphin Memory Engine démarré avec PID: {dme_process.pid}")
                except Exception as e:
                    print(f"Erreur lors du lancement de Dolphin Memory Engine: {str(e)}")
                    print("Continuons sans Dolphin Memory Engine...")
            else:
                print("Dolphin Memory Engine introuvable, continuons sans...")
            
            # Attendre que Memory Engine se connecte
            print("Attente de la connexion de Memory Engine...")
            time.sleep(3)
            
            # Initialiser le jeu
            print("Initialisation du jeu...")
            try:
                game, contexte = initialize_game()
                
                if game and contexte:
                    print("Jeu initialisé avec succès")
                    return jsonify({"success": True, "message": "Dolphin started successfully"})
                else:
                    print("Échec de l'initialisation du jeu")
                    return jsonify({"error": "Failed to initialize game"}), 500
            except Exception as e:
                print(f"Erreur lors de l'initialisation du jeu: {str(e)}")
                return jsonify({"error": f"Erreur lors de l'initialisation du jeu: {str(e)}"}), 500
                
        except Exception as e:
            print(f"Erreur générale lors du démarrage de Dolphin: {str(e)}")
            return jsonify({"error": str(e)}), 500
            
    elif request.method == 'DELETE':
        try:
            if dolphin_process:
                print("Arrêt de Dolphin...")
                cleanup_existing_processes()
                dolphin_process = None
                game = None
                contexte = None
                print("Dolphin arrêté avec succès")
                return jsonify({"success": True, "message": "Dolphin stopped successfully"})
            else:
                print("Dolphin n'est pas en cours d'exécution")
                return jsonify({"error": "Dolphin is not running"}), 404
                
        except Exception as e:
            print(f"Erreur lors de l'arrêt de Dolphin: {str(e)}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/restart', methods=['POST'])
def restart_game():
    """Redémarre le jeu Monopoly"""
    global game, contexte
    
    try:
        # Réinitialiser le jeu
        game, contexte = initialize_game()
        
        if game is None:
            return jsonify({'success': False, 'error': 'Impossible d\'initialiser le jeu. Vérifiez les fichiers manifeste et de sauvegarde.'}), 500
        
        # Redémarrer Dolphin si demandé
        restart_dolphin = request.json.get('restart_dolphin', False)
        if restart_dolphin:
            return manage_dolphin()
        
        return jsonify({'success': True, 'message': 'Jeu redémarré'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """Gère la configuration de l'application"""
    if request.method == 'GET':
        # Renvoyer la configuration actuelle avec les valeurs par défaut
        config_data = {
            'dolphinPath': config.DOLPHIN_PATH,
            'isoPath': config.MONOPOLY_ISO_PATH,
            'refreshInterval': config.REFRESH_INTERVAL
        }
        return jsonify(config_data)
    
    if request.method == 'POST':
        try:
            # Mettre à jour la configuration
            data = request.json
            
            # Mettre à jour les variables de configuration
            if 'dolphinPath' in data:
                config.DOLPHIN_PATH = data['dolphinPath']
            if 'isoPath' in data:
                config.MONOPOLY_ISO_PATH = data['isoPath']
            if 'refreshInterval' in data:
                config.REFRESH_INTERVAL = int(data['refreshInterval'])
            
            # Sauvegarder la configuration dans un fichier
            config_file = os.path.join(config.WORKSPACE_DIR, 'user_config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return jsonify({'success': True, 'message': 'Configuration updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/dolphin/status')
def get_dolphin_status():
    """Renvoie l'état actuel de Dolphin"""
    try:
        is_running = dolphin_process is not None and dolphin_process.poll() is None
        is_game_initialized = game is not None
        
        return jsonify({
            'running': is_running,
            'game_initialized': is_game_initialized,
            'message': 'Dolphin is running and game is initialized' if is_running and is_game_initialized
                      else 'Dolphin is running' if is_running
                      else 'Dolphin is not running'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create_demo_image')
def create_demo_image():
    """Crée une image de démonstration pour Dolphin"""
    try:
        # Créer un dossier static/img s'il n'existe pas
        img_dir = os.path.join('static', 'img')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        
        # Chemin de l'image de démonstration
        demo_img_path = os.path.join(img_dir, 'dolphin_demo.png')
        
        # Créer une image simple avec du texte
        from PIL import Image, ImageDraw
        
        # Créer une image noire
        img = Image.new('RGB', (800, 600), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Ajouter du texte
        draw.text((400, 300), "Dolphin Emulator", fill=(255, 255, 255))
        draw.text((400, 330), "Running Monopoly", fill=(255, 255, 255))
        
        # Sauvegarder l'image
        img.save(demo_img_path)
        
        return jsonify({'success': True, 'message': 'Demo image created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def run_app():
    """Démarre l'application Flask"""
    # Créer le dossier de contexte s'il n'existe pas
    os.makedirs(config.CONTEXT_DIR, exist_ok=True)
    os.makedirs(config.CONTEXT_HISTORY_DIR, exist_ok=True)
    
    # Démarrer le thread de capture du terminal
    terminal_thread = threading.Thread(target=capture_terminal_output, daemon=True)
    terminal_thread.start()
    
    # Démarrer l'application Flask
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG, use_reloader=False)

if __name__ == "__main__":
    run_app() 