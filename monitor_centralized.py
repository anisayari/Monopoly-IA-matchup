"""
Monitor centralisé qui communique avec le serveur principal
"""
import dolphin_memory_engine as dme
import re
import time
import sys
import json
import base64
import requests
from pathlib import Path
from datetime import datetime
import pyautogui
import pygetwindow as gw
import win32gui
import mss
import mss.tools
from PIL import Image
import keyboard
from src.utils.calibration import CalibrationUtils
from src.utils import property_manager, get_coordinates
import difflib
from dotenv import load_dotenv
import os
from omniparser_adapter import adapt_omniparser_response
from PIL import Image
import io

# Charger les variables d'environnement depuis .env
load_dotenv()

# Vérifier que les clés API sont chargées
print("[Monitor] Checking environment variables...")
print(f"[Monitor] OpenAI API Key: {'✅ Found' if os.getenv('OPENAI_API_KEY') else '❌ Not found'}")
print(f"[Monitor] Anthropic API Key: {'✅ Found' if os.getenv('ANTHROPIC_API_KEY') else '❌ Not found'}")
print(f"[Monitor] Gemini API Key: {'✅ Found' if os.getenv('GEMINI_API_KEY') else '❌ Not found'}")

# Désactiver le fail-safe PyAutoGUI (temporaire)
pyautogui.FAILSAFE = False

class CentralizedMonitor:
    def __init__(self, api_url="http://localhost:5000"):
        # Nettoyer et valider l'URL
        api_url = str(api_url).strip().strip('`').strip('"').strip("'")
        if not api_url.startswith(('http://', 'https://')):
            print(f"⚠️  URL invalide fournie: {api_url}")
            api_url = "http://localhost:5000"
        
        self.api_url = api_url
        self.running = False
        self.already_seen = set()
        self.message_addresses = []
        self.load_game_config()
        
        self.monitor_config = self.load_monitor_config()
        self.hardcoded_buttons = self.load_hardcoded_buttons()
        self.calibration = CalibrationUtils()
    
    def load_json_config(self, file_path):
        """Charge un fichier de configuration JSON générique"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {file_path}: {e}")
            return {}

    def load_hardcoded_buttons(self):
        """Charge la configuration des boutons hardcodés"""
        return self.load_json_config('game_files/hardcoded_button.json').get('properties', {})

    def load_monitor_config(self):
        """Charge la configuration du monitor"""
        return self.load_json_config('monitor_config.json')
    
    def load_game_config(self):
        """Charge les adresses des messages depuis starting_state.jsonc"""
        try:
            with open('game_files/starting_state.jsonc', 'r', encoding='utf-8') as f:
                # Enlever les commentaires du JSONC
                content = f.read()
                # Simple regex pour enlever les commentaires //
                import re as regex
                content = regex.sub(r'//.*', '', content)
                # Parser le JSON
                config = json.loads(content)
                
                # Charger les messages
                if 'messages' in config and 'events' in config['messages']:
                    for event in config['messages']['events']:
                        self.message_addresses.append({
                            'id': event.get('id', ''),
                            'type': event.get('type', 'pattern'),
                            'address': event.get('address', ''),
                            'pattern': event.get('pattern', ''),
                            'group': event.get('group', 'other')
                        })
                    print(f"✅ Chargé {len(self.message_addresses)} messages depuis starting_state.jsonc")
                else:
                    print("⚠️  Aucun message trouvé dans starting_state.jsonc")
        except Exception as e:
            print(f"❌ Erreur lors du chargement de starting_state.jsonc: {e}")
    
    def connect_to_dolphin(self):
        """Se connecte à Dolphin Memory Engine"""
        try:
            dme.hook()
            print("✅ Connecté à Dolphin")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def get_dolphin_window(self):
        """Trouve la fenêtre Dolphin"""
        try:
            # Essayer d'abord avec le titre exact
            windows = gw.getWindowsWithTitle("SMPP69")
            for w in windows:
                if "monopoly" in w.title.lower() and w.width > 0 and w.height > 0:
                    print(f"🖼️ Fenêtre trouvée: {w.title}")
                    return w
        except:
            pass
        return None
    
    def capture_screenshot(self):
        """Capture un screenshot, l'enregistre dans /captures et le retourne en base64"""
        try:
            win = self.get_dolphin_window()
            if not win:
                return None, None
            else:
                self.focus_dolphin_window()
                time.sleep(0.5)  # Attendre que la fenêtre soit bien au premier plan

            # Debug: afficher les coordonnées
            print(f"📐 Fenêtre Dolphin: left={win.left}, top={win.top}, width={win.width}, height={win.height}")
            
            # Pour mss, on doit spécifier left, top, width, height correctement
            with mss.mss() as sct:
                monitor = {
                    "left": win.left,
                    "top": win.top,
                    "width": win.width,
                    "height": win.height
                }
                img = sct.grab(monitor)
                
                # Convertir en base64
                from io import BytesIO
                img_pil = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')
                buffer = BytesIO()
                img_pil.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

                # Enregistrer dans le dossier /captures
                captures_dir = Path("captures")
                captures_dir.mkdir(exist_ok=True)
                filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
                filepath = captures_dir / filename
                img_pil.save(filepath)
                print(f"🖼️ Screenshot enregistré dans {filepath}")
                
                # Debug: vérifier la taille de l'image capturée
                print(f"📸 Image capturée: {img_pil.size[0]}x{img_pil.size[1]} pixels")
                
                # Retourner l'image base64 ET les dimensions de la fenêtre
                return img_base64, (win.left, win.top, win.width, win.height)
        except Exception as e:
            print(f"⚠️  Erreur screenshot: {e}")
            return None, None
    
    def scan_memory(self):
        """Scan la mémoire pour les popups et messages"""
        RAM_START = 0x90000000
        RAM_SIZE = 0x00200000
        CHUNK_SIZE = 0x10000
        MAX_LENGTH = 400
        results = []
        
        for addr in range(RAM_START, RAM_START + RAM_SIZE, CHUNK_SIZE):
            try:
                chunk = dme.read_bytes(addr, CHUNK_SIZE)
                for key in self.monitor_config['keywords'].keys():
                    key_compiled = re.compile(re.escape(key.encode("utf-16-le")), re.DOTALL)
                    for match in key_compiled.finditer(chunk):
                        start_pos = match.start()
                        
                        end_offset = min(start_pos + MAX_LENGTH, len(chunk))
                        message_bytes = chunk[start_pos:end_offset]
                        
                        terminator = message_bytes.find(b"\x00\x00\x00\x00")
                        if terminator != -1:
                            message_bytes = message_bytes[:terminator]
                        
                        results.append({
                            'type': 'popup',  # Tout est traité comme popup...
                            'trigger': key,
                            'bytes':message_bytes
                        })
            except:
                pass
        
        return results
    
    def get_emoji_category(category):
        # Emojis par catégorie
        category_emojis = {
            "jail": "🔒",
            "money": "💰",
            "auction": "🔨",
            "property": "🏠",
            "trade": "🤝",
            "turn": "🎲",
            "card": "🃏",
            "property_management": "📊",
            "rent": "💸",
            "general": "🎮",
            "status": "⚠️",
            "roll dice": "🎲",
            "other": "📨"
        }
        emoji = category_emojis.get(category, "📨")
        
        return emoji
    
    def process_popup(self, popup_text, screenshot_base64, trigger):
        category = ''
        """Traite un popup en deux étapes: analyse puis décision"""
        try:
            # Étape 1: Analyser le screenshot avec OmniParser
            print("📸 Analyse du screenshot...")
            max_retries = 10
            for attempt in range(1, max_retries + 1):
                analyze_response = requests.post(
                    f"{self.api_url}/api/popups/analyze",
                    json={'screenshot_base64': screenshot_base64},
                    timeout=30
                )
                if analyze_response.ok:
                    break
                else:
                    print(f"❌ Erreur analyse: {analyze_response.status_code} (tentative {attempt}/{max_retries})")
                    if attempt < max_retries:
                        time.sleep(1)
            else:
                return None
            
            analysis = analyze_response.json()
            
            img_data = base64.b64decode(screenshot_base64)
            img = Image.open(io.BytesIO(img_data))
            img_width, img_height = img.size
            
            analysis = adapt_omniparser_response(analysis, img_width, img_height)

            monitor_keywords = self.monitor_config.get('keywords', {})
            
            icon_options = [opt for opt in analysis.get('options', []) if opt.get('type') == 'icon']
            detected_icons = [opt.get('name', '').strip().lower() for opt in icon_options]
            
            trigger_found = trigger in monitor_keywords
            selected_keywords = None
            
            if trigger_found:
                trigger_icons = [icon.strip().lower() for icon in monitor_keywords[trigger].get('icon', []) if isinstance(icon, str) and icon.strip()]
                matching_trigger_icons = [icon for icon in trigger_icons if icon in detected_icons]
                
                if matching_trigger_icons:
                    selected_keywords = [trigger]
                    print(f"✅ Trigger '{trigger}' trouvé et icônes présentes: {matching_trigger_icons}")
                else:
                    print(f"⚠️ Trigger '{trigger}' trouvé mais aucune icône correspondante détectée")
                    print(f"   Icônes attendues: {trigger_icons}")
                    print(f"   Icônes détectées: {detected_icons[:5]}...")  # Afficher les 5 premières
                    trigger_found = False  # Forcer la recherche par icônes
            
            if not trigger_found or selected_keywords is None:
                print(f"🔍 Trigger '{trigger}' non trouvé, recherche via les icônes...")
                print(f"🔍 Icônes détectées: {detected_icons}")
                
                # Chercher les keywords avec le meilleur match
                best_match = None
                best_match_ratio = 0
                best_match_count = 0
                
                for keyword, data in monitor_keywords.items():
                    icons_in_config = [icon.strip().lower() for icon in data.get('icon', []) if isinstance(icon, str) and icon.strip()]
                    
                    # Skip si pas d'icônes configurées
                    if not icons_in_config:
                        continue
                    
                    # Compter combien d'icônes sont trouvées
                    found_icons = []
                    for config_icon in icons_in_config:
                        if config_icon in detected_icons:
                            found_icons.append(config_icon)
                    
                    found_count = len(found_icons)
                    total_count = len(icons_in_config)
                    ratio = found_count / total_count if total_count > 0 else 0
                    
                    if found_count > 0:
                        if found_count == total_count:
                            print(f"✅ Keyword '{keyword}' - TOUTES les icônes trouvées ({found_count}/{total_count}): {found_icons}")
                        else:
                            print(f"⚠️ Keyword '{keyword}' - {found_count}/{total_count} icônes trouvées: {found_icons}")
                        
                        if ratio > best_match_ratio or (ratio == best_match_ratio and found_count > best_match_count):
                            best_match = keyword
                            best_match_ratio = ratio
                            best_match_count = found_count
                
                #DETECTER LA CATEGORY ICI !!! (GPT IMAGE???)

                if best_match:
                    if best_match_ratio == 1.0:
                        print(f"✅ Match parfait trouvé: '{best_match}'")
                    else:
                        print(f"✅ Meilleur match partiel: '{best_match}' ({best_match_count} icônes, ratio {best_match_ratio:.1%})")
                    selected_keywords = [best_match]
                else:
                    selected_keywords = None
                    print(f"❌ Aucun keyword trouvé (aucune icône ne correspond)")
                    
            if selected_keywords:
                all_icons = [
                    icon.strip().lower()
                    for k in selected_keywords
                    for icon in self.monitor_config['keywords'][k].get('icon', [])
                    if isinstance(icon, str)
                ]
                options = [opt for opt in icon_options if opt.get('name', '').strip().lower() in all_icons]
            else:
                options = []
            
            print(f"🔍 Options détectées: {options}")
            if options == []:
                # Mapping des options automatiques (sans IA)
                auto_options = {
                    'ok': 'ok',
                    'continue': 'continue',
                    'house rules': 'next',
                    'continue without saving/loading': 'continue without saving/loading',
                    'click': 'CLICK',
                    'press to continue': 'CLICK'
                }
                
                for opt in icon_options:
                    option_name = opt.get('name', '').strip().lower()
                    
                    if option_name in auto_options:
                        decision = auto_options[option_name]
                        print(f"✅ Option '{opt.get('name', '')}' détectée, clic direct sans IA !")
                        
                        return {
                            'success': True,
                            'decision': decision,
                            'reason': f"Option '{opt.get('name', '')}' détectée, clic direct sans IA.",
                            'options': [opt],
                            'analysis': analysis
                        }

                print(f"🔍 Aucune option détectée, skipping AI decision...")
                return None
            
            # Vérifier si "shake the Wii" est dans le texte détecté (deuxième vérification après l'analyse)
            raw_content = analysis.get('raw_parsed_content', [])
            all_text = ' '.join([item.get('content', '') for item in raw_content if item.get('type') == 'text']).lower()
            
            # Étape 2: Obtenir le contexte du jeu
            game_context = {}
            try:
                context_response = requests.get(f"{self.api_url}/api/context", timeout=5)
                if context_response.ok:
                    game_context = context_response.json()
                    
                    # Mettre à jour le current player depuis la RAM via la fonction centralisée
                    from src.utils.property_helpers import get_current_player_from_ram
                    current_player = get_current_player_from_ram()
                    if current_player:
                        game_context['global']['current_player'] = current_player
                        print(f"🎮 Current player from RAM: {current_player}")
                    
                    # Stocker le contexte pour utilisation dans _handle_trade_event
                    self.game_context = game_context
                    # Le contexte est maintenant envoyé au serveur d'actions
                    # pour être affiché dans le terminal dédié
                else:
                    game_context = {}
            except Exception as e:
                print(f"⚠️ Erreur contexte: {e}")
                game_context = {}
            
            print('CATEGORY DETECTE \n ------------------- \n :', category)
            # Étape 3: Demander la décision à l'IA directement
            print("🤖 Demande de décision à l'IA...")
            
            # Préparer la requête pour l'IA (basée uniquement sur les icônes)
            ai_request = {
                'popup_text': popup_text,
                'options': [option['name'] for option in options],  # Liste des noms d'options
                'game_context': game_context,
                'full_options': options,  # Infos complètes des options avec bbox
                'keywords': selected_keywords,  # Keywords identifiés via les icônes
                'all_detected_icons': detected_icons,  # Toutes les icônes détectées
                'category':category
            }
            
            # Appeler directement le serveur AI sur le port 7000
            ai_decision_url = "http://localhost:7000"
            decision_response = requests.post(
                f"{ai_decision_url}/api/decide",
                json=ai_request
            )
            
            if not decision_response.ok:
                print(f"❌ Erreur décision IA: {decision_response.status_code}")
                print(f"🔍 Erreur détaillée: {decision_response.text}")
                print(f"🔍 Erreur détaillée: {decision_response.json()}")
                return None
            
            decision_data = decision_response.json()
            print(f"📦 Réponse complète de l'IA: {decision_data}")
            decision = decision_data.get('decision')
            reason = decision_data.get('reason', '')
            
            print(f"✅ Décision: {decision} - {reason}")
            
            # Sauvegarder l'action de l'IA
            try:
                action_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'trigger': trigger,
                    'keywords': selected_keywords,
                    'options': [opt['name'] for opt in options],
                    'decision': decision,
                    'reason': reason,
                    'game_context': {
                        'current_player': game_context.get('global', {}).get('current_player', 'Unknown'),
                        'current_turn': game_context.get('global', {}).get('current_turn', 0),
                        'money': {player_data.get('name', player_key): player_data.get('money', 0) 
                                for player_key, player_data in game_context.get('players', {}).items()}
                    }
                }
                
                # Envoyer l'action au serveur pour sauvegarde
                requests.post(
                    f"{self.api_url}/api/actions/save",
                    json=action_data,
                    timeout=2
                )
                print(f"💾 Action sauvegardée")
            except Exception as e:
                print(f"⚠️ Erreur sauvegarde action: {e}")
            
            # Préparer les données de trade si c'est un événement de trade
            trade_data = None
            # Vérifier soit par keywords, soit par catégorie, soit par décision
            if (decision == 'make_trade'):
                trade_data = decision_data.get('trade_data', {})
                print(f"📦 Trade data extrait: {trade_data}")
                
            auction_data = None
            if (decision == 'make_auction'):
                auction_data = decision_data.get('auction_data', {})
                print(f"📦 Auction data extrait: {auction_data}")
            
            property_management_data = None
            if (decision == 'make_property_management'):
                property_management_data = decision_data.get('property_management_data', {})
                print(f"📦 Property management data extrait: {property_management_data}")
            
            # Retourner toutes les infos nécessaires
            result = {
                'success': True,
                'decision': decision,
                'reason': reason,
                'options': options,
                'analysis': analysis,
                'category': category  # IMPORTANT: Retourner la catégorie corrigée
            }
            
            # Ajouter trade_data si disponible
            if trade_data:
                result['trade_data'] = trade_data
            if auction_data:
                result['auction_data'] = auction_data
            if property_management_data:
                result['property_management_data'] = property_management_data
            return result
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return None
    
    def notify_message(self, message_text, message_category):
        """Notifie le serveur d'un nouveau message dans la RAM"""
        try:
            url = f"{self.api_url}/api/messages/detected"
            
            response = requests.post(
                url,
                json={
                    'text': message_text,
                    'category': message_category,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'centralized_monitor'
                },
                timeout=5
            )
            
            if response.ok:
                return True
            else:
                # Si l'endpoint n'existe pas, ce n'est pas grave
                return False
                
        except Exception as e:
            # Ne pas afficher d'erreur si l'endpoint n'existe pas
            return False
       
    def execute_click(self, decision, popup_data):
        """Exécute le clic selon la décision"""
        try:
            print(f"popup_data: {popup_data}")
            # Récupérer les coordonnées depuis les données du popup
            if 'options' in popup_data:
                for option in popup_data['options']:
                    # Comparer en enlevant les espaces au début et à la fin
                    if option.get('name', '').strip().lower() == decision.strip().lower():
                        # Les coordonnées sont déjà en pixels absolus
                        bbox = option.get('bbox', [])
                        if len(bbox) == 4 and 'window_bbox' in popup_data:
                            win_bbox = popup_data['window_bbox']
                            
                            # bbox contient déjà des coordonnées en pixels
                            x1, y1, x2, y2 = bbox
                            
                            # Centre de la bbox
                            if decision == 'CLICK':
                                x1 = win_bbox[2] // 2
                                y1 = win_bbox[3] // 2
                                x2 = x1
                                y2 = y1

                            cx = (x1 + x2) // 2
                            cy = (y1 + y2) // 2
                            
                            # Transformer les coordonnées (window_bbox utilisé implicitement par transform_coordinates)
                            abs_x, abs_y, transformed_cx, transformed_cy = self.transform_coordinates(cx, cy)
                            
                            if abs_x is not None:
                                print(f"🖱️  Clic sur '{decision}'")
                                print(f"   - Bbox originale: {bbox}")
                                print(f"   - Centre transformé: ({transformed_cx}, {transformed_cy})")
                                
                                # Effectuer le clic avec offset de 30 pixels
                                self.perform_click(abs_x, abs_y, f"Clic sur '{decision}'", y_offset=30)
                            else:
                                print(f"❌ Erreur de transformation pour '{decision}'")
                            
                            # Déplacer la souris au centre de la fenêtre
                            center_x = win_bbox[0] + win_bbox[2]//2
                            center_y = win_bbox[1] + 200
                            pyautogui.moveTo(center_x, center_y, duration=0.3)
                            
                            return True
            
            print(f"⚠️  Impossible de trouver les coordonnées pour '{decision}'")
            return False
            
        except Exception as e:
            print(f"❌ Erreur lors du clic: {e}")
            return False
    
    def transform_coordinates(self, x, y, window=None):
        """
        Transforme des coordonnées relatives ou pixels en coordonnées absolues
        
        Args:
            x: Coordonnée X (relative ou pixel)
            y: Coordonnée Y (relative ou pixel)
            window: Fenêtre de référence (si None, utilise get_dolphin_window)
            
        Returns:
            Tuple (abs_x, abs_y, transformed_x, transformed_y) ou (None, None, None, None) si erreur
        """
        try:
            if window is None:
                window = self.get_dolphin_window()
                if not window:
                    return None, None, None, None
            
            # Appliquer inverse_conversion
            transformed_x, transformed_y = self.calibration.inverse_conversion(x, y)
            
            # Position absolue
            abs_x = window.left + transformed_x
            abs_y = window.top + transformed_y
            
            return abs_x, abs_y, transformed_x, transformed_y
            
        except Exception as e:
            print(f"❌ Erreur lors de la transformation des coordonnées: {e}")
            return None, None, None, None
    
    def perform_click(self, x, y, description="", y_offset=0):
        """
        Effectue un clic aux coordonnées données avec la séquence mouseDown/mouseUp
        
        Args:
            x: Coordonnée X absolue
            y: Coordonnée Y absolue
            description: Description du clic pour les logs
            y_offset: Décalage Y optionnel (par défaut 0)
        """
        try:
            if description:
                print(f"🖱️  {description} à ({x}, {y + y_offset})")
            
            # Focus la fenêtre
            self.focus_dolphin_window()
            time.sleep(0.5)
            
            # Effectuer le clic
            pyautogui.moveTo(x, y + y_offset, duration=0.3)
            time.sleep(0.3)
            self.focus_dolphin_window()
            pyautogui.mouseDown()
            time.sleep(0.2)
            pyautogui.mouseUp()
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Erreur lors du clic: {e}")
    
    def focus_dolphin_window(self):
        """Focus la fenêtre Dolphin"""
        win = self.get_dolphin_window()
        if win:
            try:
                win.activate()
            except:
                try:
                    win32gui.SetForegroundWindow(win._hWnd)
                except:
                    pass
            time.sleep(0.1)
    
    def _handle_auction_event(self, auction_data, result, screenshot):
        """
        Gère les événements d'enchère via modification RAM après un clic initial
        
        Args:
            auction_data: Structure avec les enchères max et le gagnant
                {
                    'player1': {'max_bid': 250},
                    'player2': {'max_bid': 300},
                    'winner': 'player2',
                    'winning_bid': 300
                }
            result: Résultat du process_popup
            screenshot: Capture d'écran actuelle
        """
        # Obtenir la fenêtre Dolphin pour les clics
        dolphin_window = gw.getWindowsWithTitle("SMPP69")
        if not dolphin_window:
            print("❌ Fenêtre Dolphin non trouvée")
            return
        
        win = dolphin_window[0]
        
        try:
            print("💰 Gestion de l'enchère détectée")
            print(f"🔧 Mode de modification: RAM uniquement")
            print(f"\n----------------\nAUCTION DATA\n----------------\n {auction_data}")
            
            # Récupérer les infos de l'enchère
            winner = auction_data.get('winner')
            winning_bid = auction_data.get('winning_bid', 0)
            player1_max = auction_data.get('player1', {}).get('max_bid', 0)
            player2_max = auction_data.get('player2', {}).get('max_bid', 0)
            
            # Récupérer le contexte du jeu pour savoir qui est le joueur actuel
            game_context = self.game_context if hasattr(self, 'game_context') else {}
            global_data = game_context.get('global', {})
            
            # Déterminer qui commence l'enchère (le joueur actuel)
            current_player_id = global_data.get('current_player', 'player1')
            other_player_id = 'player2' if current_player_id == 'player1' else 'player1'
            
            # Mapper les noms des joueurs
            players = game_context.get('players', {})
            current_player_name = players.get(current_player_id, {}).get('name', current_player_id)
            other_player_name = players.get(other_player_id, {}).get('name', other_player_id)
            
            print(f"📍 Joueur qui commence: {current_player_name} ({current_player_id})")
            print(f"📍 Autre joueur: {other_player_name} ({other_player_id})")
            print(f"🏆 Gagnant de l'enchère: {winner} avec ${winning_bid}")
            
            # Mapper le gagnant à l'ID du joueur
            winner_id = None
            # Le winner vient maintenant sous forme "player1" ou "player2"
            if winner in ['player1', 'player2']:
                winner_id = winner
                winner_name = players.get(winner_id, {}).get('name', winner_id)
                print(f"🏆 Gagnant mappé: {winner_name} ({winner_id})")
            else:
                # Ancienne logique pour compatibilité
                if winner == current_player_name:
                    winner_id = current_player_id
                elif winner == other_player_name:
                    winner_id = other_player_id
                else:
                    print(f"⚠️ Impossible de mapper le gagnant '{winner}' à un joueur")
                    return
            
            # Utiliser la modification RAM avec un clic initial
            print("\n🔧 Mode RAM: Clic initial puis modification directe de la mémoire")
            self._handle_auction_via_ram(winner_id, winning_bid, win)
            
        except Exception as e:
            print(f"❌ Erreur lors de la gestion de l'enchère: {e}")
            import traceback
            traceback.print_exc()

    def _handle_property_management_event(self, property_data, result, screenshot):
        """
        Gère les événements de gestion de propriétés (achat/vente de maisons, hypothèques)
        
        Args:
            property_data: Structure avec les actions à effectuer
                {
                    "decisions": {
                        "properties": [
                            {
                                "property_name": "Park Place",
                                "action": "buy_house",
                                "quantity": 1
                            }
                        ]
                    }
                }
            result: Résultat du process_popup
            screenshot: Capture d'écran actuelle
        """
        # Obtenir la fenêtre Dolphin pour les clics
        dolphin_window = gw.getWindowsWithTitle("SMPP69")
        if not dolphin_window:
            print("❌ Fenêtre Dolphin non trouvée")
            return
        
        win = dolphin_window[0]
        
        try:
            print("🏠 Gestion des propriétés détectée")
            print(f"\n----------------\nPROPERTY DATA\n----------------\n {property_data}")
            
            # Extraire les décisions depuis la nouvelle structure
            decisions = property_data.get('decisions', {})
            property_actions = decisions.get('properties', [])
            
            if not property_actions:
                print("⚠️ Aucune action de propriété trouvée")
                return
            
            # Mapper les actions aux boutons correspondants
            action_button_map = {
                'buy_house': 'button_buy_1_property',
                'buy_houses': 'button_buy_1_property',
                'buy_set': 'button_buy_set_property',
                'sell_house': 'button_sell_1_property',
                'sell_houses': 'button_sell_1_property', 
                'sell_set': 'button_sell_set_property',
                'mortgage': 'button_mortgage_property',
                'unmortgage': 'button_unmortgage_property'
            }
            
            # Traiter chaque action de propriété individuellement
            for property_action in property_actions:
                prop_name = property_action.get('property_name')
                action = property_action.get('action')
                quantity = property_action.get('quantity', 1)
                
                if not prop_name or not action:
                    print(f"⚠️ Action invalide: {property_action}")
                    continue
                
                # Récupérer le bouton correspondant à l'action
                button_key = action_button_map.get(action)
                if not button_key:
                    print(f"❌ Action '{action}' non reconnue")
                    continue
                    
                action_button = self.hardcoded_buttons.get(button_key)
                if not action_button:
                    print(f"❌ Bouton '{button_key}' non trouvé dans hardcoded_buttons")
                    continue
                
                # Traiter l'action sur cette propriété
                coords = get_coordinates(prop_name, 'relative')
                if coords:
                    rel_x, rel_y = coords
                    
                    # Transformer les coordonnées
                    abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                        rel_x * win.width, 
                        rel_y * win.height, 
                        win
                    )
                    
                    if abs_x is not None:
                        print(f"\n🏠 Traitement de la propriété: {prop_name}")
                        print(f"   📋 Action: {action} (quantité: {quantity})")
                        
                        # Répéter l'action selon la quantité
                        for i in range(quantity):
                            if quantity > 1:
                                print(f"   🔢 Itération {i+1}/{quantity}")
                            
                            # 1. Cliquer sur la propriété
                            print(f"   1️⃣ Clic sur la propriété")
                            self.perform_click(abs_x, abs_y, f"Clic sur {prop_name}", y_offset=6)
                            time.sleep(0.5)
                            
                            # 2. Cliquer sur le bouton d'action
                            action_abs_x, action_abs_y, _, _ = self.transform_coordinates(
                                action_button['x_relative'] * win.width,
                                action_button['y_relative'] * win.height,
                                win
                            )
                            
                            if action_abs_x is not None:
                                print(f"   2️⃣ Clic sur le bouton: {action}")
                                self.perform_click(action_abs_x, action_abs_y, f"Clic sur {action}",y_offset=6)
                                time.sleep(1)
                            
                            # 3. Si c'est une action qui nécessite confirmation, gérer les boutons yes/no
                            if action in ['mortgage', 'sell_house', 'sell_houses', 'sell_set']:
                                # Chercher le bon bouton de confirmation
                                if action == 'mortgage':
                                    yes_button_key = 'button_yes_mortgage_property'
                                elif action in ['sell_house', 'sell_houses', 'sell_set']:
                                    yes_button_key = 'button_yes_sell_property'
                                
                                yes_button = self.hardcoded_buttons.get(yes_button_key)
                                
                                if yes_button:
                                    yes_abs_x, yes_abs_y, _, _ = self.transform_coordinates(
                                        yes_button['x_relative'] * win.width,
                                        yes_button['y_relative'] * win.height,
                                        win
                                    )
                                    
                                    if yes_abs_x is not None:
                                        time.sleep(1)
                                        print(f"   3️⃣ Clic sur YES pour confirmer")
                                        self.perform_click(yes_abs_x, yes_abs_y, "Clic sur YES",y_offset=6)
                                        time.sleep(1)
                        
                        # 4. Cliquer sur "Done" pour valider cette propriété (après toutes les itérations)
                        done_button = self.hardcoded_buttons.get('button_done_property')
                        if done_button:
                            done_abs_x, done_abs_y, _, _ = self.transform_coordinates(
                                done_button['x_relative'] * win.width,
                                done_button['y_relative'] * win.height,
                                win
                            )
                            
                            if done_abs_x is not None:
                                print(f"   4️⃣ Clic sur Done pour valider")
                                self.perform_click(done_abs_x, done_abs_y, "Clic sur Done",y_offset=6)
                                time.sleep(1)
                        
                        print(f"   ✅ Propriété {prop_name} traitée")
                    else:
                        print(f"❌ Erreur de transformation pour {prop_name}")
                else:
                    print(f"⚠️ Coordonnées introuvables pour {prop_name}")
            
            # Fin du traitement de toutes les propriétés
            print("\n✅ Toutes les propriétés ont été traitées")
                    
        except Exception as e:
            print(f"❌ Erreur lors de la gestion des propriétés: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_auction_via_ram(self, winner_id, winning_bid, win):
        """
        Gère l'enchère via modification directe de la RAM après un clic initial
        1. Player1 commence toujours : 1 clic si player1 gagne, 2 clics si player2 gagne
        2. Modifie la RAM pour définir le montant final et le gagnant
        """
        print("🔧 Mode RAM: Clic(s) initial(aux) sur 'oui' puis modification directe")
        
        # Récupérer le bouton "oui" pour le clic initial
        yes_button = self.hardcoded_buttons.get('button_yes_auction')
        if not yes_button:
            print("❌ Bouton 'oui' de l'enchère non trouvé dans hardcoded_buttons")
            return
        
        # Déterminer le nombre de clics selon le gagnant
        clicks_count = 1 if winner_id == 'player1' else 2
        print(f"🎯 Gagnant: {winner_id} - Nombre de clics nécessaires: {clicks_count}")
        
        # Effectuer le(s) clic(s) sur "oui"
        for i in range(clicks_count):
            print(f"🖱️ Clic #{i+1} sur 'oui'")
            abs_x, abs_y, _, _ = self.transform_coordinates(
                yes_button['x_relative'] * win.width,
                yes_button['y_relative'] * win.height,
                win
            )
            
            if abs_x is not None:
                self.perform_click(abs_x, abs_y, f"Clic OUI #{i+1}/{clicks_count}")
                time.sleep(1.5)  # Attendre entre les clics
            else:
                print("❌ Erreur de transformation des coordonnées pour le bouton 'oui'")
                return
        
        # Adresses RAM pour le current bid
        AUCTION_BID_FRONT_ADDRESS = 0x8053D0A6  # Adresse front (current bid)
        AUCTION_BID_BACK_ADDRESS = 0x9303A2DA   # Adresse back (current bid)
        
        print(f"\n📝 Modification RAM:")
        print(f"   - Enchère finale: ${winning_bid}")
        print(f"   - Gagnant: {winner_id}")
        print(f"   - Écriture à l'adresse front {AUCTION_BID_FRONT_ADDRESS:08X}: ${winning_bid}")
        print(f"   - Écriture à l'adresse back {AUCTION_BID_BACK_ADDRESS:08X}: ${winning_bid}")
        # Écrire le montant de l'enchère aux deux adresses
        try:
            # Écrire le winning_bid aux deux adresses (front et back) - halfword (2 bytes)
            dme.write_bytes(AUCTION_BID_FRONT_ADDRESS, winning_bid.to_bytes(2, 'big'))
            dme.write_bytes(AUCTION_BID_BACK_ADDRESS, winning_bid.to_bytes(2, 'big'))
            print("✅ Enchère configurée via RAM avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de l'écriture en RAM: {e}")
            print("⚠️ Vérifiez que Dolphin Memory Engine est connecté")
        
        # Cliquer sur "no" pour terminer l'enchère
        no_button = self.hardcoded_buttons.get('button_no_auction')
        if no_button:
            print("\n🖱️ Clic final sur 'no' pour terminer l'enchère")
            abs_x, abs_y, _, _ = self.transform_coordinates(
                no_button['x_relative'] * win.width,
                no_button['y_relative'] * win.height,
                win
            )
            
            if abs_x is not None:
                time.sleep(1.5)  # Attendre un peu après l'écriture RAM
                self.perform_click(abs_x, abs_y, "Clic final NO pour terminer l'enchère")
                print("✅ Enchère terminée")
            else:
                print("❌ Erreur de transformation des coordonnées pour le bouton 'no'")
        else:
            print("❌ Bouton 'no' de l'enchère non trouvé dans hardcoded_buttons")
    
    def _handle_trade_event(self, trade_data, result, screenshot):
        """
        Gère les événements de trade en cliquant sur les propriétés
        
        Args:
            trade_data: Structure avec les offres des joueurs
            result: Résultat du process_popup
            screenshot: Capture d'écran actuelle
        """

        # Obtenir la fenêtre Dolphin pour les clics
        dolphin_window = gw.getWindowsWithTitle("SMPP69")
        if not dolphin_window:
            print("❌ Fenêtre Dolphin non trouvée")
            return
        
        win = dolphin_window[0]
        win_x, win_y = win.left, win.top

        def get_coord_cash_button(player):
            # Map player to button key
            button_mapping = {
                'player1': 'add_cash_player_1',
                'player2': 'add_cash_player_2'
            }
            
            if player not in button_mapping:
                return
            
            button_key = button_mapping[player]
            coord = self.hardcoded_buttons[button_key]
            
            abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                coord['x_relative'] * win.width,
                coord['y_relative'] * win.height,
                win
            )
            
            return abs_x, abs_y
        
        def click_on_calculette(list_number):
            list_button_number_calculette = []
            for num in range(0,10):
                list_button_number_calculette.append(f"button_{num}_calculette")
            
            dict_button_number_calculette = {}
            for button in list_button_number_calculette:
                dict_button_number_calculette[button] = self.hardcoded_buttons[button]
            for _num in list_number:
                coord = dict_button_number_calculette[f"button_{_num}_calculette"]
                rel_x,rel_y = coord['x_relative'] , coord['y_relative']
                abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                    rel_x * win.width, 
                    rel_y * win.height, 
                    win
                )
                self.perform_click(abs_x, abs_y, f"Click on {_num}")
            
            coord_ok_button = self.hardcoded_buttons['button_ok_calculette']
            rel_x,rel_y = coord_ok_button['x_relative'] , coord_ok_button['y_relative']
            abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                    rel_x * win.width, 
                    rel_y * win.height, 
                    win
                )
                
            self.perform_click(abs_x, abs_y, "Click ok button calculette")
            time.sleep(2)

        try:
            print("🔄 Gestion du trade détectée")
            print(f"\n----------------\nTRADE DATA\n----------------\n {trade_data}")
            # Récupérer le contexte du jeu pour savoir qui est le joueur actuel
            game_context = self.game_context if hasattr(self, 'game_context') else {}
            current_player = game_context.get('global', {}).get('current_player', 'player1')
            other_player = 'player2' if current_player == 'player1' else 'player1'
            
            for _player in [current_player,other_player]:
                coord = self.hardcoded_buttons[f'header_{_player}']
                abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                            coord['x_relative'] * win.width, 
                            coord['y_relative'] * win.height, win)
                self.perform_click(abs_x,abs_y, f"click on {_player}")

            if trade_data.get('status') == "no_deal":
                print('LES IAS ne sont pas mis d\'accord sur un DEAL ! :-( )')
                print('Click sur cancel')
                coord_cancel_button = self.hardcoded_buttons['cancel_trade']
                rel_x,rel_y = coord_cancel_button['x_relative'], coord_cancel_button['y_relative']
                # Transformer les coordonnées
                abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                        rel_x * win.width, 
                        rel_y * win.height, win)
                self.perform_click(abs_x, abs_y, "Click sur Cancel")
                time.sleep(2)
                return

            print(f"📍 Joueur actuel: {current_player}")
            print(f"📍 Ordre de clic: propriétés de {other_player} puis {current_player}")
            
            # Liste ordonnée des joueurs : d'abord l'autre joueur, puis le joueur actuel
            players_order = [other_player, current_player]
            
            # Ajouter les propriétés dans l'ordre spécifié
            properties_to_click = []
            for player in players_order:
                # Récupérer les propriétés de manière sûre (retourne [] si absent)
                props = trade_data.get(player, {}).get('offers', {}).get('properties', [])
                print(f"Propriétés : {props}")

                properties_to_click.extend((prop, player) for prop in props)
            
            # Cliquer sur toutes les propriétés dans l'ordre
            print(f"🏠 Total de propriétés à cliquer: {len(properties_to_click)}")

            
            for prop_name, owner in properties_to_click:
                coords = get_coordinates(prop_name, 'relative')
                if coords:
                    rel_x, rel_y = coords
                    
                    # Transformer les coordonnées
                    abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                        rel_x * win.width, 
                        rel_y * win.height, 
                        win
                    )
                    
                    if abs_x is not None:
                        print(f"🏠 Propriété: {prop_name} (appartient à {owner})")
                        print(f"   - Coordonnées relatives: ({rel_x:.3f}, {rel_y:.3f})")
                        print(f"   - Après transformation: ({transformed_x}, {transformed_y})")
                        
                        # Effectuer le clic
                        self.perform_click(abs_x, abs_y, f"Clic sur {prop_name}", y_offset=6)
                    else:
                        print(f"❌ Erreur de transformation pour {prop_name}")
                else:
                    print(f"⚠️ Coordonnées introuvables pour {prop_name}")
            
            # Extract money data for both players using a loop
            money_requested = {}
            for player_num in [1, 2]:
                player_key = f'player{player_num}'
                money_requested[player_key] = trade_data.get(player_key, {}).get('offers', {}).get('money', 0)
                print(f"Money Player {player_num}: {money_requested[player_key]}")
                if int(money_requested[player_key]) > 0: 
                    abs_x, abs_y = get_coord_cash_button(player_key)
                    self.perform_click(abs_x, abs_y, f"Clic sur Cash")
                    time.sleep(2)
                    list_number = list(str(money_requested[player_key]))
                    click_on_calculette(list_number)

            coord_propose_button = self.hardcoded_buttons['propose_trade']
            rel_x, rel_y = coord_propose_button['x_relative'], coord_propose_button['y_relative']
            abs_x, abs_y, transformed_x, transformed_y = self.transform_coordinates(
                    rel_x * win.width, 
                    rel_y * win.height, 
                    win
                )
            self.perform_click(abs_x,abs_y, "Click sur propose")
            time.sleep(2)
            self.perform_click(abs_x,abs_y, "Click sur propose")
                    
        except Exception as e:
            print(f"❌ Erreur lors de la gestion du trade: {e}")
    
    def display_player_info(self):
        """Affiche les informations des joueurs et leurs modèles AI"""
        try:
            # Récupérer les paramètres du jeu
            response = requests.get(f"{self.api_url}/api/game-settings", timeout=5)
            if response.status_code == 200:
                settings = response.json()
                
                print("🎮 === Configuration des Joueurs ===")
                
                if 'players' in settings:
                    for player_id, player_info in settings['players'].items():
                        name = player_info.get('name', 'Unknown')
                        provider = player_info.get('provider', 'openai')
                        model = player_info.get('ai_model', 'unknown')
                        
                        # Symboles pour les providers
                        provider_symbols = {
                            'openai': '🤖',
                            'anthropic': '🧠',
                            'gemini': '💎'
                        }
                        symbol = provider_symbols.get(provider, '🎲')
                        
                        # Nom du provider
                        provider_names = {
                            'openai': 'OpenAI',
                            'anthropic': 'Anthropic',
                            'gemini': 'Google Gemini'
                        }
                        provider_name = provider_names.get(provider, provider.title())
                        
                        # Afficher les informations
                        print(f"{symbol} {name.upper()}: {provider_name} - {model}")
                
                print("================================\n")
        except Exception as e:
            print(f"⚠️  Impossible de charger les informations des joueurs: {e}\n")
    
    def run(self):
        """Boucle principale du monitor"""
        print("\n🔍 Démarrage du monitoring centralisé...")
        print(f"📡 Serveur API: {self.api_url}")
        print("📊 Appuyez sur Ctrl+C pour arrêter\n")
        
        # Afficher les informations des joueurs
        self.display_player_info()
        
        if not self.connect_to_dolphin():
            return
        
        scan_count = 0

        self.running = True
        
        while self.running:
            # Lire et afficher le current player
            from src.utils.property_helpers import get_current_player_from_ram
            current_player = get_current_player_from_ram()
            if current_player:
                print(f"🔍 Scanning memory... (Current player: {current_player})")
            else:
                print("🔍 Scanning memory...")
            matches = self.scan_memory() 
            scan_count += 1
        
            if scan_count >= 3:
                print("🛠️ Forçage d'un match factice pour simulation (capture + décision)")
                fake_match = {
                    'type': 'popup',
                    'trigger': 'would you like',  # Utiliser un trigger qui existe dans monitor_config
                    'group': 'turn'
                }
                matches = [fake_match]
                scan_count = 0

            for match in matches[:1]:
                print(f"🔍 Match: {match}")
                raw_text = match['bytes'].decode('utf-16-le', errors='ignore')
                cleaned_text = ''.join(c for c in raw_text if 32 <= ord(c) < 127)
                
                key = f"{cleaned_text[:40]}"
                
                if key not in self.already_seen :
                    
                    self.already_seen.add(key)
                    print(f"✨ Popup interactif détecté: \"{match['trigger']}\"")
                    
                    time.sleep(0.1)
                    
                    screenshot, window_info = self.capture_screenshot()
                    
                    if screenshot:
                        print(f"🖼️ Screenshot capturé !")
                        
                        result = self.process_popup(cleaned_text, screenshot, match.get('trigger'))
                        category = result['category']
                            
                        print('RESULT: ',result)
                        if result is None:
                            print("🔍 No result found, skipping...")
                            continue
                        if result and result.get('success'):
                            
                            # Vérifier si la décision est "make_trade" (depuis ai_service)
                            if category == "trade" and result.get('decision') == 'make_trade':
                                print("🔄 Décision 'make_trade' détectée depuis ai_service")
                                trade_data = result.get('trade_data', {})
                                print(f'TRADE_DATA {trade_data}')
                                if trade_data:
                                    self._handle_trade_event(trade_data, result, screenshot)
                                    continue
                                else:
                                    print("⚠️ Aucune donnée de trade trouvée dans le résultat")

                            elif category == "auction" and result.get('decision') == 'make_auction':
                                print("🔄 Décision 'make_auction' détectée depuis ai_service")
                                auction_data = result.get('auction_data', {})
                                print(f'AUCTION_DATA {auction_data}')
                                if auction_data:
                                    # TODO: Gérer l'enchère
                                    self._handle_auction_event(auction_data, result, screenshot)
                                    continue
                                else:
                                    print("⚠️ Aucune donnée d'enchère trouvée dans le résultat")

                            elif category == "property" and result.get('decision') == 'make_property_management':
                                print("🔄 Décision 'make_property_management' détectée depuis ai_service")
                                property_management_data = result.get('property_management_data', {})
                                print(f'PROPERTY_MANAGEMENT_DATA {property_management_data}')
                                if property_management_data:
                                    self._handle_property_management_event(property_management_data, result, screenshot)
                                    continue
                                else:
                                    print("⚠️ Aucune donnée de gestion de propriété trouvée dans le résultat")
                            
                            decision = result['decision']
                            options = result.get('options', [])
                            
                            selected_option = None
                            for opt in options:
                                if opt['name'].strip().lower() == decision.strip().lower():
                                    selected_option = opt
                                    break
                            
                            if not selected_option:
                                for opt in options:
                                    opt_name = opt['name'].strip().lower()
                                    dec_name = decision.strip().lower()
                                    if dec_name in opt_name or opt_name in dec_name:
                                        selected_option = opt
                                        break
                            
                            if selected_option and window_info:
                                popup_data = {
                                    'window_bbox': window_info,
                                    'options': options
                                }
                                
                                # Exécuter le clic
                                if self.execute_click(decision, popup_data):
                                    # Attendre un peu plus longtemps avant de retirer de already_seen
                                    time.sleep(3)
                            else:
                                print(f"⚠️ Option '{decision}' non trouvée dans les options disponibles")
                            
                            # Retirer pour re-détecter
                            self.already_seen.remove(key)
            
            time.sleep(1)


if __name__ == "__main__":
    # Permettre de spécifier l'URL du serveur
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    # Nettoyer l'URL des caractères indésirables
    api_url = api_url.strip().strip('`').strip('"').strip("'")
    
    # Valider l'URL
    if not api_url.startswith(('http://', 'https://')):
        print(f"⚠️  URL invalide: {api_url}")
        print("   Utilisation de l'URL par défaut: http://localhost:5000")
        api_url = "http://localhost:5000"
    
    monitor = CentralizedMonitor(api_url)
    monitor.run()