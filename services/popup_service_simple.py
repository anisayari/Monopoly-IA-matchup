"""
Service simplifié pour les popups - sans event bus
"""
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional
import uuid

class SimplePopupService:
    """Service simplifié pour gérer les popups avec des appels API directs"""
    
    def __init__(self, omniparser_url="http://localhost:8002", ai_decision_url="http://localhost:7000"):
        self.omniparser_url = omniparser_url
        self.ai_decision_url = ai_decision_url
        self.active_popups: Dict[str, dict] = {}
    
    def process_popup(self, popup_text: str, screenshot_base64: str, game_context: dict = None) -> dict:
        """
        Traite un popup de A à Z et retourne la décision
        1. Analyse le screenshot avec OmniParser
        2. Demande une décision à l'IA
        3. Retourne la décision
        """
        popup_id = str(uuid.uuid4())[:8]
        
        try:
            # 1. Analyser le screenshot avec OmniParser
            print(f"[POPUP] Analyse du screenshot...")
            omniparser_response = requests.post(
                f"{self.omniparser_url}/parse/",
                json={"base64_image": screenshot_base64},
                timeout=30
            )
            
            if not omniparser_response.ok:
                return {
                    'success': False,
                    'error': f"OmniParser error: {omniparser_response.status_code}"
                }
            
            omniparser_result = omniparser_response.json()
            parsed_content = omniparser_result.get('parsed_content_list', [])
            
            # Extraire les options (boutons)
            options = []
            for item in parsed_content:
                if item.get('type') == 'text':
                    text = item.get('content', '').lower()
                    
                    # Détecter les boutons Monopoly
                    button_keywords = [
                        'ok', 'cancel', 'yes', 'no', 'confirm', 'accept', 'decline', 'pay',
                        'accounts', 'next turn', 'roll again', 'auction', 'buy', 'back', 
                        'trade', 'pay bail', 'roll dice', 'use card', 'bid', 'deal', 
                        'no deal', 'propose', 'request cash', 'add cash', 'mortgage',
                        'buy 1', 'buy set', 'sell 1', 'sell set', 'done'
                    ]
                    
                    if any(keyword in text for keyword in button_keywords):
                        options.append({
                            'name': text,
                            'original_text': item.get('content', ''),
                            'bbox': item.get('bbox', []),
                            'confidence': item.get('confidence', 1.0),
                            'type': 'button'
                        })
                
                elif item.get('type') == 'icon':
                    options.append({
                        'name': item['content'].lower(),
                        'bbox': item.get('bbox', []),
                        'confidence': item.get('confidence', 1.0),
                        'type': 'icon'
                    })
            
            print(f"[POPUP] Options trouvées: {[opt['name'] for opt in options]}")
            
            # 2. Demander une décision à l'IA
            print(f"[POPUP] Demande de décision à l'IA...")
            
            # Préparer les données pour l'IA
            ai_request = {
                'popup_text': popup_text,
                'options': [opt['name'] for opt in options],
                'game_context': game_context or {},
                'full_options': options,  # Inclure toutes les infos pour le calcul des coordonnées
                'parsed_content': parsed_content
            }
            
            ai_response = requests.post(
                f"{self.ai_decision_url}/api/decide",
                json=ai_request,
                timeout=300  # 5 minutes pour permettre les longues conversations
            )
            
            if not ai_response.ok:
                return {
                    'success': False,
                    'error': f"AI decision error: {ai_response.status_code}"
                }
            
            ai_result = ai_response.json()
            decision = ai_result.get('decision')
            reason = ai_result.get('reason', '')
            
            print(f"[POPUP] Décision IA: {decision} - Raison: {reason}")
            
            # 3. Trouver les coordonnées pour la décision
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
            
            # Préparer la réponse
            result = {
                'success': True,
                'popup_id': popup_id,
                'decision': decision,
                'reason': reason,
                'options': options,
                'selected_option': selected_option
            }
            
            # Stocker temporairement pour référence
            self.active_popups[popup_id] = {
                'text': popup_text,
                'decision': decision,
                'reason': reason,
                'options': options,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Nettoyer après 30 secondes
            import threading
            threading.Timer(30.0, lambda: self.active_popups.pop(popup_id, None)).start()
            
            return result
            
        except Exception as e:
            print(f"[POPUP] Erreur: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_popup_status(self, popup_id: str) -> Optional[dict]:
        """Récupère le statut d'un popup"""
        return self.active_popups.get(popup_id)