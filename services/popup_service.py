"""
Service centralisé pour la gestion des popups
"""
import json
import time
from datetime import datetime
from typing import Dict, Optional
import requests
from .event_bus import EventBus, EventTypes

class PopupService:
    """Gère la détection, l'analyse et les décisions des popups"""
    
    def __init__(self, event_bus: EventBus, omniparser_url="http://localhost:8000", unified_server_url="http://localhost:7000"):
        self.event_bus = event_bus
        self.omniparser_url = omniparser_url
        self.unified_server_url = unified_server_url
        self.active_popups: Dict[str, dict] = {}
        
        # S'abonner aux événements
        self.event_bus.subscribe(EventTypes.POPUP_DETECTED, self._on_popup_detected)
        self.event_bus.subscribe(EventTypes.AI_DECISION_MADE, self._on_decision_made)
    
    def register_popup(self, popup_data: dict) -> str:
        """Enregistre un nouveau popup détecté"""
        popup_id = popup_data.get('id') or self._generate_id()
        
        # Enrichir les données
        popup_data['id'] = popup_id
        popup_data['detected_at'] = datetime.utcnow().isoformat()
        popup_data['status'] = 'detected'
        
        # Stocker
        self.active_popups[popup_id] = popup_data
        
        # Publier l'événement
        self.event_bus.publish(
            EventTypes.POPUP_DETECTED,
            popup_data,
            source='popup_service'
        )
        
        return popup_id
    
    def analyze_popup(self, popup_id: str, screenshot_base64: str) -> dict:
        """Analyse un popup avec OmniParser"""
        if popup_id not in self.active_popups:
            raise ValueError(f"Popup {popup_id} not found")
        
        try:
            # Appeler OmniParser
            response = requests.post(
                f"{self.omniparser_url}/parse/",
                json={"base64_image": screenshot_base64},
                timeout=30
            )
            
            if response.ok:
                result = response.json()
                parsed_content = result.get('parsed_content_list', [])
                
                # Extraire toutes les informations (texte + icônes)
                options = []
                text_content = []
                
                for item in parsed_content:
                    if item.get('type') == 'text':
                        text = item.get('content', '').lower()
                        text_content.append(item.get('content', ''))
                        
                        # Détecter tous les boutons et options Monopoly
                        button_keywords = [
                            'ok', 'cancel', 'yes', 'no', 'confirm', 'accept', 'decline', 'pay',
                            'accounts', 'next turn', 'roll again', 'auction', 'buy', 'back', 
                            'trade', 'pay bail', 'roll dice', 'use card', 'bid', 'deal', 
                            'no deal', 'propose', 'request cash', 'add cash', 'mortage',
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
                        # Les icônes peuvent aussi être des boutons
                        print(f"🤖 Icon: {item['content']}")
                        options.append({
                            'name': item['content'].lower(),
                            'bbox': item.get('bbox', []),
                            'confidence': item.get('confidence', 1.0),
                            'type': 'icon'
                        })
                
                # Mettre à jour le popup avec toutes les infos
                self.active_popups[popup_id]['options'] = options
                self.active_popups[popup_id]['text_content'] = text_content
                self.active_popups[popup_id]['raw_parsed_content'] = parsed_content
                self.active_popups[popup_id]['status'] = 'analyzed'
                self.active_popups[popup_id]['analyzed_at'] = datetime.utcnow().isoformat()
                
                # Déterminer le type de popup
                popup_type = self._determine_popup_type(text_content, options)
                self.active_popups[popup_id]['popup_type'] = popup_type
                
                # Publier l'événement
                self.event_bus.publish(
                    EventTypes.POPUP_ANALYZED,
                    {
                        'popup_id': popup_id,
                        'options': options,
                        'text_content': text_content,
                        'popup_type': popup_type
                    },
                    source='popup_service'
                )
                
                return {'success': True, 'options': options, 'text_content': text_content}
            else:
                raise Exception(f"OmniParser error: {response.status_code}")
                
        except Exception as e:
            # Publier l'erreur
            self.event_bus.publish(
                EventTypes.SERVICE_ERROR,
                {
                    'service': 'omniparser',
                    'error': str(e),
                    'popup_id': popup_id
                },
                source='popup_service'
            )
            return {'success': False, 'error': str(e)}
    
    def request_ai_decision(self, popup_id: str, game_context: dict) -> None:
        """Demande une décision à l'IA"""
        if popup_id not in self.active_popups:
            raise ValueError(f"Popup {popup_id} not found")
        
        popup = self.active_popups[popup_id]
        print(f"🤖 Popup: {popup}")
        
        # Publier la demande de décision
        self.event_bus.publish(
            EventTypes.AI_DECISION_REQUESTED,
            {
                'popup_id': popup_id,
                'popup_text': popup.get('text', ''),
                'options': popup.get('options', []),
                'game_context': game_context
            },
            source='popup_service'
        )
    
    def execute_decision(self, popup_id: str, decision: str, coordinates: tuple) -> bool:
        """Exécute une décision (clic)"""
        if popup_id not in self.active_popups:
            return False
        
        # Mettre à jour le statut
        self.active_popups[popup_id]['status'] = 'executed'
        self.active_popups[popup_id]['decision'] = decision
        self.active_popups[popup_id]['executed_at'] = datetime.utcnow().isoformat()
        
        # Publier l'événement
        self.event_bus.publish(
            EventTypes.POPUP_EXECUTED,
            {
                'popup_id': popup_id,
                'decision': decision,
                'coordinates': coordinates
            },
            source='popup_service'
        )
        
        # Nettoyer après un délai
        self._schedule_cleanup(popup_id, delay=5)
        
        return True
    
    def get_popup_status(self, popup_id: str) -> Optional[dict]:
        """Récupère le statut d'un popup"""
        return self.active_popups.get(popup_id)
    
    def get_active_popups(self) -> list:
        """Récupère tous les popups actifs"""
        return list(self.active_popups.values())
    
    def _on_popup_detected(self, event: dict):
        """Callback quand un popup est détecté"""
        data = event['data']
        if 'screenshot_base64' in data:
            # Analyser automatiquement
            popup_id = data['id']
            print(f"[EVENT] Auto-analyzing popup {popup_id} from event")
            analysis_result = self.analyze_popup(popup_id, data['screenshot_base64'])
            
            if analysis_result.get('success'):
                # Récupérer le contexte du jeu
                try:
                    # Importer ici pour éviter les imports circulaires
                    from src.game.contexte import GameContext
                    context = GameContext()
                    game_context = context.get_state()
                except:
                    game_context = {}
                
                # Demander une décision à l'IA
                self.request_ai_decision(popup_id, game_context)
    
    def _on_decision_made(self, event: dict):
        """Callback quand une décision est prise"""
        data = event['data']
        popup_id = data.get('popup_id')
        if popup_id in self.active_popups:
            self.active_popups[popup_id]['decision'] = data.get('decision')
            self.active_popups[popup_id]['decision_reason'] = data.get('reason')
    
    def _schedule_cleanup(self, popup_id: str, delay: int = 5):
        """Planifie le nettoyage d'un popup"""
        import threading
        def cleanup():
            time.sleep(delay)
            if popup_id in self.active_popups:
                del self.active_popups[popup_id]
        
        threading.Thread(target=cleanup, daemon=True).start()
    
    def _generate_id(self) -> str:
        """Génère un ID unique"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _determine_popup_type(self, text_content: list, options: list) -> str:
        """Détermine le type de popup basé sur le contenu"""
        full_text = ' '.join(text_content).lower()
        
        # Patterns spécifiques de popups Monopoly
        if 'would you like to' in full_text:
            return 'turn_options'  # Choix de tour (accounts, next turn, roll again)
        elif 'you want to buy' in full_text:
            return 'property_purchase'  # Achat de propriété (auction, buy)
        elif 'a property you own' in full_text:
            return 'property_management'  # Gestion propriétés (back, trade)
        elif 'chance' in full_text:
            return 'chance_card'
        elif 'in jail' in full_text:
            return 'jail_decision'  # Prison (Pay Bail, Roll Dice, Use Card)
        elif 'community chest' in full_text:
            return 'community_chest'
        elif 'bid' in full_text and any(opt['name'] in ['yes', 'no'] for opt in options):
            return 'auction_bid'
        elif 'accounts' in full_text and len(options) == 1:
            return 'accounts_info'  # Juste OK
        elif 'accounts' in full_text and any(opt['name'] in ['back', 'trade'] for opt in options):
            return 'accounts_management'  # Back, Trade
        elif 'select player' in full_text:
            return 'trading_select_player'
        elif 'choose wich properties you want to trade' in full_text:
            return 'trading_select_properties'
        elif 'trading' in full_text and any(opt['name'] in ['cancel', 'propose'] for opt in options):
            return 'trading_negotiate'  # Cancel, Propose, Request Cash, Add Cash
        elif 'trading' in full_text and any(opt['name'] in ['deal', 'no deal'] for opt in options):
            return 'trading_confirm'  # Deal, No Deal
        elif 'pay rent' in full_text:
            return 'pay_rent'
        elif 'go to jail' in full_text:
            return 'go_to_jail'
        elif 'property deeds' in full_text:
            return 'property_deeds'  # Mortage, Buy/Sell, Done
        elif 'pay' in full_text and ('$' in full_text or 'm' in full_text):
            return 'payment_choice'
        elif len(options) == 2 and any(opt['name'] in ['ok', 'cancel'] for opt in options):
            return 'confirmation'
        elif len(options) == 1 and any(opt['name'] == 'ok' for opt in options):
            return 'information'
        else:
            return 'unknown'