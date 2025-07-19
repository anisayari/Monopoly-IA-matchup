"""
Service unifié pour la prise de décision sur les popups
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .event_bus import EventBus, EventTypes
from .ai_service import AIService
from .logging_service import LoggingService

class DecisionService:
    """Service centralisé pour prendre des décisions sur les popups"""
    
    def __init__(self, event_bus: EventBus, ai_service: AIService, logging_service: LoggingService):
        self.event_bus = event_bus
        self.ai_service = ai_service
        self.logging_service = logging_service
        
        # Charger les actions prédéfinies
        self.predefined_actions = self._load_predefined_actions()
        
        # S'abonner aux demandes de décision
        self.event_bus.subscribe('decision.requested', self._on_decision_requested)
    
    def _load_predefined_actions(self) -> dict:
        """Charge les actions prédéfinies depuis le fichier de config"""
        config_path = Path(__file__).parent.parent / "config" / "predefined_actions.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logging_service.log_error(
                    e,
                    'decision_service',
                    {'action': 'load_predefined_actions'}
                )
        
        # Configuration par défaut
        return {
            'popup_actions': {},
            'priority_order': ["buy", "next turn", "roll again", "auction", "trade", "back", "accounts", "ok"],
            'ai_fallback': True
        }
    
    def make_decision(self, popup_data: dict, game_context: dict) -> Tuple[str, str, float]:
        """
        Prend une décision pour un popup
        
        Retourne: (décision, raison, confiance)
        """
        popup_type = popup_data.get('popup_type', 'unknown')
        options = [opt['name'] for opt in popup_data.get('options', [])]
        
        self.logging_service.log(
            f"Making decision for popup type: {popup_type}",
            level='info',
            component='decision_service',
            extra={'popup_id': popup_data.get('id'), 'options': options}
        )
        
        # 1. Vérifier les actions prédéfinies
        predefined_decision = self._check_predefined_action(popup_type, options, game_context)
        if predefined_decision:
            decision, reason = predefined_decision
            self.logging_service.log(
                f"Using predefined action: {decision}",
                level='info',
                component='decision_service',
                extra={'reason': reason}
            )
            return decision, reason, 0.95
        
        # 2. Si IA disponible et fallback activé
        if self.ai_service.available and self.predefined_actions.get('ai_fallback', True):
            self.logging_service.log(
                "No predefined action, requesting AI decision",
                level='info',
                component='decision_service'
            )
            
            ai_result = self.ai_service.make_decision(
                popup_data.get('text', ''),
                popup_data.get('options', []),
                game_context
            )
            
            return ai_result['choice'], ai_result['reason'], ai_result['confidence']
        
        # 3. Utiliser la priorité par défaut
        default_decision = self._get_default_decision(options)
        return default_decision, "Priorité par défaut", 0.5
    
    def _check_predefined_action(self, popup_type: str, options: List[str], game_context: dict) -> Optional[Tuple[str, str]]:
        """Vérifie s'il y a une action prédéfinie pour ce type de popup"""
        popup_actions = self.predefined_actions.get('popup_actions', {})
        
        if popup_type not in popup_actions:
            return None
        
        config = popup_actions[popup_type]
        
        # Vérifier les conditions
        conditions = config.get('conditions', {})
        for condition, action in conditions.items():
            if action in options and self._evaluate_condition(condition, game_context):
                return action, f"Condition '{condition}' remplie"
        
        # Action par défaut pour ce type
        default = config.get('default')
        if default and default in options:
            return default, f"Action par défaut pour {popup_type}"
        
        return None
    
    def _evaluate_condition(self, condition: str, game_context: dict) -> bool:
        """Évalue une condition basée sur le contexte du jeu"""
        # Récupérer les infos du joueur actuel
        current_player = self._get_current_player(game_context)
        if not current_player:
            return False
        
        money = current_player.get('money', 0)
        
        # Conditions simples
        conditions_map = {
            'low_money': money < 200,
            'money_below_500': money < 500,
            'money_above_1000': money > 1000,
            'early_game': game_context.get('global', {}).get('current_turn', 0) < 10,
            'late_game': game_context.get('global', {}).get('current_turn', 0) > 30,
            'has_get_out_card': current_player.get('get_out_of_jail_cards', 0) > 0,
            'can_buy_house': self._can_buy_house(current_player, game_context),
            'need_money': money < 100,
            'strategic_property': True,  # Simplification - toujours vrai pour l'instant
            'good_trade': True,  # Simplification
            'completes_color_group': True,  # Simplification
            'already_owns_color_group': self._owns_color_group(current_player, game_context),
            'complete_color_group_possible': True  # Simplification
        }
        
        return conditions_map.get(condition, False)
    
    def _get_current_player(self, game_context: dict) -> Optional[dict]:
        """Récupère le joueur actuel depuis le contexte"""
        # Simplification - prendre le premier joueur
        players = game_context.get('players', {})
        if players:
            return list(players.values())[0]
        return None
    
    def _can_buy_house(self, player: dict, game_context: dict) -> bool:
        """Vérifie si le joueur peut acheter une maison"""
        # Simplification - vérifier juste l'argent
        return player.get('money', 0) > 500
    
    def _owns_color_group(self, player: dict, game_context: dict) -> bool:
        """Vérifie si le joueur possède un groupe de couleur complet"""
        # Simplification - toujours False pour l'instant
        return False
    
    def _get_default_decision(self, options: List[str]) -> str:
        """Retourne la décision par défaut basée sur la priorité"""
        priority_order = self.predefined_actions.get('priority_order', [])
        
        for priority in priority_order:
            if priority in options:
                return priority
        
        # Si aucune priorité, prendre la première option
        return options[0] if options else 'none'
    
    def _on_decision_requested(self, event: dict):
        """Callback quand une décision est demandée"""
        data = event['data']
        popup_data = data.get('popup_data', {})
        print(f"🤖 Popup data: {popup_data}")
        game_context = data.get('game_context', {})
        print(f"🤖 Game context: {game_context}")
        
        # Prendre la décision
        decision, reason, confidence = self.make_decision(popup_data, game_context)
        
        # Publier le résultat
        self.event_bus.publish(
            'decision.made',
            {
                'popup_id': popup_data.get('id'),
                'decision': decision,
                'reason': reason,
                'confidence': confidence
            },
            source='decision_service'
        )
        
        # Logger la décision
        self.logging_service.log_popup(
            popup_data.get('id'),
            'decision_made',
            {
                'decision': decision,
                'reason': reason,
                'confidence': confidence,
                'popup_type': popup_data.get('popup_type')
            }
        )