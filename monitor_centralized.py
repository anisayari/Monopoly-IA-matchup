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
        self.patterns = []
        self.message_addresses = []
        self.load_game_config()
        self.setup_patterns()
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
        return self.load_json_config('game_files/hardcoded_buttons.json')

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
        
    def setup_patterns(self):
        """Configure les patterns de recherche unifiés"""
        self.unified_patterns = []
        
        # Ajouter les patterns de popups
        popup_keywords = {
            "would you like to": "turn",
            "you want to buy": "property", 
            "a Property you own": "property",
            "chance": "card",
            "Community Chest": "card",
            "in jail": "jail",
            "Pay Rent": "rent",
            "Trading": "trade",
            "trading": "trade",
            "auction": "auction",
            "Go To Jail": "jail",
            "property deeds": "property_management",
            "shake the Wii":"roll dice"
        }
        
        for trigger, category in popup_keywords.items():
            self.unified_patterns.append({
                'id': trigger.lower().replace(' ', '_'),  # ID basé sur le trigger
                'trigger': trigger,
                'category': category,
                'pattern': trigger,
                'compiled': re.compile(re.escape(trigger.encode("utf-16-le")), re.DOTALL),
                'type': 'popup',
                'max_length': 400,
                'group': category,
                'address': None
            })
        
        # # Ajouter les patterns de messages
        # for msg in self.message_addresses:
        #     if msg['type'] == 'pattern' and msg['pattern']:
        #         category = self._get_message_category(msg['id'], msg['pattern'])
                
        #         self.unified_patterns.append({
        #             'id': msg['id'],
        #             'trigger': msg['pattern'],  # Le pattern fait office de trigger
        #             'category': category,
        #             'pattern': msg['pattern'],
        #             'compiled': re.compile(re.escape(msg['pattern'].encode("utf-16-le")), re.IGNORECASE | re.DOTALL),
        #             'type': 'message',
        #             'max_length': 200,
        #             'group': msg.get('group', 'other'),
        #             'address': msg.get('address', '')
        #         })
    
    def _get_message_category(self, msg_id, pattern):
        """Détermine la catégorie d'un message basé sur son ID ou pattern"""
        msg_id_lower = msg_id.lower()
        pattern_lower = pattern.lower()
        
        if 'jail' in msg_id_lower or 'jail' in pattern_lower:
            return 'jail'
        elif 'auction' in msg_id_lower or 'bid' in msg_id_lower or 'auction' in pattern_lower:
            return 'auction'
        elif 'buy' in msg_id_lower or 'sell' in msg_id_lower or 'house' in msg_id_lower or 'hotel' in msg_id_lower or 'mortgage' in msg_id_lower:
            return 'property'
        elif 'trade' in msg_id_lower or 'deal' in msg_id_lower:
            return 'trade'
        elif 'pay' in msg_id_lower or 'collect' in msg_id_lower or 'money' in pattern_lower or 'tax' in msg_id_lower:
            return 'money'
        elif 'roll' in msg_id_lower or 'dice' in msg_id_lower or 'turn' in msg_id_lower:
            return 'turn'
        elif 'chance' in msg_id_lower or 'community' in msg_id_lower or 'card' in msg_id_lower:
            return 'card'
        elif 'bankrupt' in msg_id_lower:
            return 'status'
        elif 'rent' in msg_id_lower:
            return 'rent'
        elif 'roll' in msg_id_lower or 'dice' in msg_id_lower or 'turn' in msg_id_lower:
            return 'roll dice'
        else:
            return 'other'
    
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
        
        unified_results = []
        
        for addr in range(RAM_START, RAM_START + RAM_SIZE, CHUNK_SIZE):
            try:
                chunk = dme.read_bytes(addr, CHUNK_SIZE)
                
                # Scan avec les patterns unifiés
                for pattern_info in self.unified_patterns:
                    for match in pattern_info['compiled'].finditer(chunk):
                        start_pos = match.start()
                        match_addr = addr + start_pos
                        
                        end_offset = min(start_pos + pattern_info['max_length'], len(chunk))
                        message_bytes = chunk[start_pos:end_offset]
                        
                        terminator = message_bytes.find(b"\x00\x00\x00\x00")
                        if terminator != -1:
                            message_bytes = message_bytes[:terminator]
                        
                        unified_results.append({
                            'type': 'popup',  # Tout est traité comme popup
                            'id': pattern_info['id'],
                            'trigger': pattern_info['trigger'],
                            'category': pattern_info['category'],
                            'address': match_addr,
                            'bytes': message_bytes,
                            'pattern': pattern_info['pattern'],
                            'group': pattern_info['group']
                        })
            except:
                pass
        
        return unified_results
    
    def process_popup(self, popup_text, screenshot_base64, trigger,category ):
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
                        time.sleep(2)
            else:
                # Si on sort de la boucle sans break, tous les essais ont échoué
                return None
            
            analysis = analyze_response.json()
            
            # Adapter la réponse si elle vient d'OmniParser officiel
            # Récupérer les dimensions de l'image depuis le screenshot
            from PIL import Image
            import io
            img_data = base64.b64decode(screenshot_base64)
            img = Image.open(io.BytesIO(img_data))
            img_width, img_height = img.size
            
            # Adapter la réponse pour avoir des coordonnées absolues
            analysis = adapt_omniparser_response(analysis, img_width, img_height)

            
            monitor_config = self.monitor_config
            monitor_keywords = monitor_config.get('keywords', {})
            
            # Toujours récupérer les icônes pour la suite
            icon_options = [opt for opt in analysis.get('options', []) if opt.get('type') == 'icon']
            detected_icons = [opt.get('name', '').strip().lower() for opt in icon_options]
            
            # Étape 1: Vérifier si le trigger correspond directement à une clé
            trigger_found = trigger in monitor_keywords
            selected_keywords = None
            
            if trigger_found:
                # Vérifier que les icônes du trigger sont présentes
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
                # Étape 2: Utiliser les icônes pour identifier la situation
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
                        
                        # Préférer d'abord le ratio le plus élevé, puis le nombre absolu d'icônes trouvées
                        if ratio > best_match_ratio or (ratio == best_match_ratio and found_count > best_match_count):
                            best_match = keyword
                            best_match_ratio = ratio
                            best_match_count = found_count
                
                if best_match:
                    if best_match_ratio == 1.0:
                        print(f"✅ Match parfait trouvé: '{best_match}'")
                    else:
                        print(f"✅ Meilleur match partiel: '{best_match}' ({best_match_count} icônes, ratio {best_match_ratio:.1%})")
                    selected_keywords = [best_match]
                else:
                    selected_keywords = None
                    print(f"❌ Aucun keyword trouvé (aucune icône ne correspond)")
                    
                    # Vérifier "shake the wii" dans les icônes détectées
                    shake_wii_found = False
                    for icon in detected_icons:
                        if 'shake the wii' in icon.lower():
                            print(f"🎲 'shake the Wii' détecté dans l'icône: {icon}")
                            shake_wii_found = True
                            break
                    
                    # Si pas trouvé dans les icônes, vérifier dans le texte
                    if not shake_wii_found:
                        print("check if shake the wii is in the text")
                        raw_content = analysis.get('raw_parsed_content', [])
                        all_text = ' '.join([item.get('content', '') for item in raw_content if item.get('type') == 'text']).lower()
                        print(f"🔍 All text: {all_text}")
                        if 'shake the wii' in all_text:
                            shake_wii_found = True
                    
                    if shake_wii_found:
                        print("🎲 'shake the Wii' détecté - retour direct CLICK")
                        return {
                            'success': True,
                            'decision': 'CLICK',
                            'reason': "Shake the Wii détecté",
                            'options': [{
                                "bbox": [914, 510, 914, 510],  # Centre de l'écran
                                "confidence": 1.0,
                                "name": "CLICK",
                                "type": "icon"
                            }],
                            'analysis': analysis
                        }


            if selected_keywords:
                all_icons = [
                    icon.strip().lower()
                    for k in selected_keywords
                    for icon in monitor_config['keywords'][k].get('icon', [])
                    if isinstance(icon, str)
                ]
                options = [opt for opt in icon_options if opt.get('name', '').strip().lower() in all_icons]
            else:
                options = []
            
            raw_parsed_content = analysis.get('raw_parsed_content', [])
            
            print(f"🔍 Options détectées: {options}")
            if options == []:
                # Si aucune option détectée, mais qu'il y a une option 'ok' dans les icônes, clique dessus sans IA
                for opt in icon_options:
                    if opt.get('name', '').strip().lower() == 'ok':
                        print("✅ Option 'ok' détectée, clic direct sans IA !")
                        return {
                            'success': True,
                            'decision': 'ok',
                            'reason': "Option 'ok' détectée, clic direct sans IA.",
                            'options': [opt],
                            'analysis': analysis
                        }
                    elif opt.get('name', '').strip().lower() == 'continue':
                        print("✅ Option 'continue' détectée, clic direct sans IA !")
                        return {
                            'success': True,
                            'decision': 'continue',
                            'reason': "Option 'continue' détectée, clic direct sans IA.",
                            'options': [opt],
                            'analysis': analysis
                        }
                    elif opt.get('name', '').strip().lower() == 'house rules':
                        print("✅ Option 'house rules' détectée, clic direct sans IA !")
                        return {
                            'success': True,
                            'decision': 'next',
                            'reason': "Option 'house rules' détectée, clic direct sans IA.",
                            'options': [opt],
                            'analysis': analysis
                        }
                    elif opt.get('name', '').strip().lower() == 'continue without saving/loading':
                        print("✅ Option 'continue without saving/loading' détectée, clic direct sans IA !")
                        return {
                            'success': True,
                            'decision': 'continue without saving/loading',
                            'reason': "Option 'continue without saving/loading' détectée, clic direct sans IA.",
                            'options': [opt],
                            'analysis': analysis
                        }
                    elif opt.get('name', '').strip().lower() == 'CLICK' or opt.get('name', '').strip().lower() == 'press to continue':
                        print("✅ Option 'CLICK' détectée, clic direct sans IA !")
                        return {
                            'success': True,
                            'decision': 'CLICK',
                            'reason': "Option 'CLICK' détectée, clic direct sans IA.",
                            'options': [opt],   
                            'analysis': analysis
                        }
                print(f"🔍 Aucune option détectée, skipping AI decision...")
                return None
            
            # Vérifier si "shake the Wii" est dans le texte détecté
            raw_content = analysis.get('raw_parsed_content', [])
            all_text = ' '.join([item.get('content', '') for item in raw_content if item.get('type') == 'text']).lower()
            
            # Étape 2: Obtenir le contexte du jeu
            game_context = {}
            try:
                context_response = requests.get(f"{self.api_url}/api/context", timeout=5)
                if context_response.ok:
                    game_context = context_response.json()
                    # Stocker le contexte pour utilisation dans _handle_trade_event
                    self.game_context = game_context
                    # Le contexte est maintenant envoyé au serveur d'actions
                    # pour être affiché dans le terminal dédié
                else:
                    game_context = {}
            except Exception as e:
                print(f"⚠️ Erreur contexte: {e}")
                game_context = {}
            
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
            if any('Trading' in kw for kw in selected_keywords):
                trade_data = decision_data.get('trade_data', {})
            
            # Retourner toutes les infos nécessaires
            result = {
                'success': True,
                'decision': decision,
                'reason': reason,
                'options': options,
                'analysis': analysis
            }
            
            # Ajouter trade_data si disponible
            if trade_data:
                result['trade_data'] = trade_data
                
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
                                self.perform_click(abs_x, abs_y, f"Clic sur '{decision}'")
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
    
    def perform_click(self, x, y, description="", y_offset=30):
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
    
    def send_keyboard_action(self, action_type):
        """Envoie des actions clavier à Dolphin"""
        try:
            # Focus Dolphin d'abord
            self.focus_dolphin_window()
            time.sleep(0.5)
            
            if action_type == "idle_action":
                # Pour "What would you like to do?" - Flèche gauche 2x + Entrée
                print("⌨️  Envoi de: ← ← ↵")
                pyautogui.press('left')
                time.sleep(0.2)
                pyautogui.press('left')
                time.sleep(0.2)
                pyautogui.press('enter')
                
                # Notifier le serveur de l'action clavier
                try:
                    requests.post(
                        f"{self.api_url}/api/actions/keyboard",
                        json={
                            'type': 'keyboard',
                            'action': 'idle_action',
                            'description': 'Flèche gauche x2 + Entrée (What would you like to do?)',
                            'keys': ['left', 'left', 'enter'],
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        timeout=2
                    )
                except:
                    pass
                
                return True
            
            return False
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi des touches: {e}")
            return False
    
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
                        self.perform_click(abs_x, abs_y, f"Clic sur {prop_name}")
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
            print("🔍 Scanning memory...")
            matches = self.scan_memory()
            scan_count += 1

            # Simulation d'un match factice après 5 scans
            if scan_count >= 5:
                print("🛠️ Forçage d'un match factice pour simulation (capture + décision)")
                # Crée un match factice qui suit la même structure que les vrais matches
                import random
                fake_address = random.randint(0x90000000, 0x90200000)  # Adresse aléatoire pour éviter les doublons
                fake_match = {
                    'type': 'popup',
                    'id': 'fake_simulation',
                    'address': fake_address,
                    'bytes': 'Simulation forced popup'.encode('utf-16-le'),
                    'trigger': 'would you like',  # Utiliser un trigger qui existe dans monitor_config
                    'category': 'turn',
                    'pattern': 'Simulation',
                    'group': 'turn'
                }
                matches = [fake_match]
                scan_count = 0  # Reset pour pouvoir re-simuler plus tard

            for match in matches[:1]:
                print(f"🔍 Match: {match}")
                # Tous les matches sont maintenant des dictionnaires
                raw_text = match['bytes'].decode('utf-16-le', errors='ignore')
                cleaned_text = ''.join(c for c in raw_text if 32 <= ord(c) < 127)
                
                key = f"{match['type']}:{match['id']}:{match['address']:08X}:{cleaned_text[:40]}"
                
                # Cas spécial : "shake the Wii" doit toujours être traité
                force_process = False
                if match.get('trigger') == 'shake the Wii' or 'shake the wii' in cleaned_text.lower():
                    print("🎲 Détection spéciale 'shake the Wii' - forçage du traitement")
                    force_process = True
                
                if key not in self.already_seen or force_process:
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
                    emoji = category_emojis.get(match['category'], "📨")
                    
                    print(f"\n{emoji} [{match['category'].upper()}] {cleaned_text}")
                    self.already_seen.add(key)
                    
                    print(f"✨ Popup interactif détecté: \"{match['trigger']}\"")
                    
                    # Wait for UI to fully render before screenshot
                    time.sleep(0.1)
                    
                    # Capturer screenshot
                    screenshot, window_info = self.capture_screenshot()
                    
                    if screenshot:
                        print(f"🖼️ Screenshot capturé !")
                        
                        # Traiter le popup (analyse + décision)
                        result = self.process_popup(cleaned_text, screenshot, match.get('trigger'), match.get('category'))
                        if result is None:
                            print("🔍 No result found, skipping...")
                            continue
                        if result and result.get('success'):
                            # Déterminer le type d'événement basé sur les keywords ou la catégorie
                            current_event = None
                            if match.get('category') == "trade" or any('Trading' in kw for kw in match.get('keywords', [])):
                                current_event = "trade"
                            elif match.get('category') == "auction" or 'Auction' in match.get('keywords', []):
                                current_event = "auction"
                            
                            # Vérifier si la décision est "make_trade" (depuis ai_service)
                            if current_event == "trade" and result.get('decision') == 'make_trade':
                                print("🔄 Décision 'make_trade' détectée depuis ai_service")
                                trade_data = result.get('trade_data', {})
                                print(f'TRADE_DATA {trade_data}')
                                if trade_data:
                                    self._handle_trade_event(trade_data, result, screenshot)
                                    continue
                                else:
                                    print("⚠️ Aucune donnée de trade trouvée dans le résultat")
                            
                            decision = result['decision']
                            options = result.get('options', [])
                            
                            # Trouver l'option sélectionnée
                            selected_option = None
                            for opt in options:
                                # Comparaison avec strip() pour ignorer les espaces
                                if opt['name'].strip().lower() == decision.strip().lower():
                                    selected_option = opt
                                    break
                            
                            if not selected_option:
                                # Essayer une correspondance partielle
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