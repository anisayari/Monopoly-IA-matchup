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
import difflib

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
        self.calibration = CalibrationUtils()
    
    def load_monitor_config(self):
        """Charge la configuration du monitor depuis monitor_config.json"""
        try:
            with open('monitor_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur lors du chargement de monitor_config.json: {e}")
            return {}
    
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
            "trading": "trade",
            "auction": "auction",
            "go to jail": "jail",
            "property deeds": "property_management"
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
        
        # Ajouter les patterns de messages
        for msg in self.message_addresses:
            if msg['type'] == 'pattern' and msg['pattern']:
                category = self._get_message_category(msg['id'], msg['pattern'])
                
                self.unified_patterns.append({
                    'id': msg['id'],
                    'trigger': msg['pattern'],  # Le pattern fait office de trigger
                    'category': category,
                    'pattern': msg['pattern'],
                    'compiled': re.compile(re.escape(msg['pattern'].encode("utf-16-le")), re.IGNORECASE | re.DOTALL),
                    'type': 'message',
                    'max_length': 200,
                    'group': msg.get('group', 'other'),
                    'address': msg.get('address', '')
                })
    
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
    
    def filter_options(self, options, selected_keywords=None):
        """Filtre les options en fonction des keywords sélectionnés (ou tous si None)"""
        if selected_keywords is not None:
            # On ne garde que les icônes des keywords sélectionnés
            all_icons = [
                icon.lower()
                for k in selected_keywords
                for icon in self.monitor_config['keywords'][k].get('icon', [])
            ]
        else:
            # Ancien comportement : tous les icônes
            all_icons = [
                icon.lower()
                for keyword in self.monitor_config.get('keywords', {}).values()
                for icon in keyword.get('icon', [])
            ]
        filtered_options = []
        for opt in options:
            print(f"🔍 Option: {opt['name']}")
            if opt['name'].lower() in all_icons:
                print(f"🔍 Option filtrée: {opt['name']}")
                filtered_options.append(opt)
        return filtered_options
    
    def process_popup(self, popup_text, screenshot_base64):
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
            text_content = analysis.get('text_content', [])
            all_text = ' '.join(text_content).lower()
            print(f"🔍 All text: {all_text}")
            candidate_keywords = []
            for keyword_key, keyword_obj in self.monitor_config.get('keywords', {}).items():
                for keyword in keyword_obj.get('text', []):
                    keyword_lower = keyword.lower()
                    keyword_words = keyword_lower.split()
                    
                    # Méthode 1 : Recherche exacte de la sous-chaîne
                    if keyword_lower in all_text:
                        candidate_keywords.append((keyword_key, 1.0))
                        print(f"✅ Keyword trouvé (exact): {keyword_key}")
                        continue
                        
                    # Méthode 2 : Vérifier si tous les mots sont présents (peu importe l'ordre)
                    all_words_found = True
                    for word in keyword_words:
                        if word not in all_text:
                            all_words_found = False
                            break
                    
                    if all_words_found:
                        # Calculer un score basé sur la proximité des mots
                        # Plus les mots sont proches, meilleur est le score
                        score = 0.85  # Score de base si tous les mots sont trouvés
                        
                        # Bonus si les mots sont dans le bon ordre et proches
                        if len(keyword_words) > 1:
                            # Chercher la distance minimale entre les mots
                            positions = []
                            for word in keyword_words:
                                pos = all_text.find(word)
                                if pos != -1:
                                    positions.append(pos)
                            
                            if len(positions) == len(keyword_words):
                                # Si les mots sont dans l'ordre et proches
                                if positions == sorted(positions):
                                    # Distance moyenne entre les mots
                                    avg_distance = sum(positions[i+1] - positions[i] for i in range(len(positions)-1)) / (len(positions)-1)
                                    if avg_distance < 20:  # Mots très proches
                                        score = 0.95
                        
                        candidate_keywords.append((keyword_key, score))
                        print(f"✅ Keyword trouvé (mots séparés): {keyword_key} (score: {score})")

            selected_keywords = [k for k, score in candidate_keywords]

            # SPECIAL CASE: If 'New turn Roll the dice' is detected, return 'CLICK' immediately
            if 'New turn Roll the dice' in selected_keywords or any('remote and press to roll the' in t.lower() for t in text_content):
                print("🎲 Detected 'New turn Roll the dice' situation, returning 'CLICK' directly.")
                return {
                    'success': True,
                    'decision': 'CLICK',
                    'reason': "Auto-detected 'New turn Roll the dice', no AI needed.",
                    'options':[{
                                "bbox": [42, 42, 42, 42],
                                "confidence": 1.0,
                                "name": "CLICK",
                                "original_text": "CLICK",
                                "type": "button"
                            }],
                    'analysis': analysis
                }

            options = analysis.get('options', [])
            options = self.filter_options(options, selected_keywords)
            raw_parsed_content = analysis.get('raw_parsed_content', [])
            
            print(f"🔍 Options détectées: {options}")
            if options == []:
                print(f"🔍 Aucune option détectée, skipping AI decision...")
                return None
            
            # Étape 2: Obtenir le contexte du jeu
            game_context = {}
            try:
                context_response = requests.get(f"{self.api_url}/api/context", timeout=2)
                if context_response.ok:
                    game_context = context_response.json()
            except:
                pass
            
            # Étape 3: Demander la décision à l'IA directement
            print("🤖 Demande de décision à l'IA...")
            
            # Préparer la requête pour l'IA (même format que avant)
            ai_request = {
                'popup_text': popup_text,
                'options': [option['name'] for option in options],  # Liste des noms d'options
                'game_context': game_context,
                'full_options': options,  # Infos complètes des options avec bbox
                'text_content': text_content,
                'parsed_content': raw_parsed_content  # Contenu parsé complet
            }
            
            # Appeler directement le serveur AI sur le port 7000
            ai_decision_url = "http://localhost:7000"
            decision_response = requests.post(
                f"{ai_decision_url}/api/decide",
                json=ai_request,
                timeout=30
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
            
            # Retourner toutes les infos nécessaires
            return {
                'success': True,
                'decision': decision,
                'reason': reason,
                'options': options,
                'analysis': analysis
            }
            
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
                    if option.get('name', '').lower() == decision.lower():
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
                            transformed_cx, transformed_cy = self.calibration.inverse_conversion(cx, cy)

                            # Position absolue (ajouter l'offset de la fenêtre)
                            # window_bbox est [x, y, width, height]
                            abs_x = win_bbox[0] + transformed_cx
                            abs_y = win_bbox[1] + transformed_cy
                            
                            print(f"🖱️  Clic sur '{decision}' à ({abs_x}, {abs_y})")
                            print(f"   - Bbox originale: {bbox}")
                            print(f"   - Centre relatif: ({transformed_cx}, {transformed_cy})")
                            print(f"   - Window position: ({win_bbox[0]}, {win_bbox[1]})")
                            
                            # Focus la fenêtre
                            self.focus_dolphin_window()
                            time.sleep(0.5)
                            
                            # Effectuer le clic
                            pyautogui.moveTo(abs_x, abs_y, duration=0.3)
                            time.sleep(0.3)
                            self.focus_dolphin_window()
                            pyautogui.mouseDown()
                            time.sleep(0.2)
                            pyautogui.mouseUp()
                            time.sleep(0.5)
                            
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
    
    def run(self):
        """Boucle principale du monitor"""
        print("\n🔍 Démarrage du monitoring centralisé...")
        print(f"📡 Serveur API: {self.api_url}")
        print("📊 Appuyez sur Ctrl+C pour arrêter\n")
        
        if not self.connect_to_dolphin():
            return
        
        scan_count = 0

        self.running = True
        
        while self.running:
            print("🔍 Scanning memory...")
            matches = self.scan_memory()
            scan_count += 1

            # Simulation d'un match factice après 15 scans
            if scan_count >= 15:
                print("🛠️ Forçage d'un match factice pour simulation (capture + décision)")
                # Crée un match factice qui suit la même structure que les vrais matches
                fake_match = {
                    'type': 'popup',
                    'id': 'fake_simulation',
                    'address': 0xDEADBEEF,
                    'bytes': 'Simulation forced popup'.encode('utf-16-le'),
                    'trigger': 'Simulation',
                    'category': 'other',
                    'pattern': 'Simulation',
                    'group': 'other'
                }
                matches = [fake_match]
                scan_count = 0  # Reset pour pouvoir re-simuler plus tard

            for match in matches[:1]:
                # Tous les matches sont maintenant des dictionnaires
                raw_text = match['bytes'].decode('utf-16-le', errors='ignore')
                cleaned_text = ''.join(c for c in raw_text if 32 <= ord(c) < 127)
                
                key = f"{match['type']}:{match['id']}:{match['address']:08X}:{cleaned_text[:40]}"
                if key not in self.already_seen:
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
                        result = self.process_popup(cleaned_text, screenshot)
                        if result is None:
                            print("🔍 No result found, skipping...")
                            continue
                        if result and result.get('success'):
                            decision = result['decision']
                            options = result.get('options', [])
                            
                            # Trouver l'option sélectionnée
                            selected_option = None
                            for opt in options:
                                if opt['name'].lower() == decision.lower():
                                    selected_option = opt
                                    break
                            
                            if not selected_option:
                                # Essayer une correspondance partielle
                                for opt in options:
                                    if decision.lower() in opt['name'].lower() or opt['name'].lower() in decision.lower():
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