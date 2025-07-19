"""
Service IA centralisé pour les décisions de jeu
Utilisé directement par unified_decision_server.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Dict, List, Optional
from openai import OpenAI
import logging
import requests
from datetime import datetime

class AIService:
    """Service IA pour prendre des décisions dans Monopoly"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.available = False
        self.game_settings = self._load_game_settings()
        
        # Initialiser OpenAI si la clé est disponible
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.available = True
                self.logger.info("✅ Service IA activé")
            except Exception as e:
                self.logger.error(f"⚠️  Erreur initialisation IA: {e}")
        else:
            self.logger.warning("⚠️  Service IA désactivé (pas de clé API)")
    
    def _load_game_settings(self):
        """Charge les paramètres du jeu depuis settings.json"""
        settings_path = os.path.join("config", "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur chargement settings: {e}")
        return {}
    
    def _send_to_monitor(self, endpoint: str, data: Dict, port: int = 8003):
        """Envoie des données aux serveurs de monitoring"""
        try:
            url = f"http://localhost:{port}/{endpoint}"
            requests.post(url, json=data, timeout=1)
        except:
            # Ignorer les erreurs si le monitor n'est pas lancé
            pass
    
    def make_decision(self, popup_text: str, options: List[str], game_context: Dict) -> Dict:
        """
        Prend une décision basée sur le contexte
        
        Args:
            popup_text: Le texte du popup
            options: Liste des options disponibles (strings)
            game_context: Contexte complet du jeu
            
        Returns:
            Dict avec 'decision', 'reason', 'confidence'
        """
        
        # Si l'IA n'est pas disponible, utiliser la logique par défaut
        if not self.available or not self.client:
            return self._default_decision(options)
        
        try:
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            
            # Déterminer quel modèle utiliser basé sur le joueur actuel
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            model = self._get_model_for_player(current_player)
            
            # Envoyer le contexte au monitor d'actions
            self._send_to_monitor('context', game_context, port=8004)
            
            # Envoyer la pensée d'analyse au monitor de chat
            self._send_to_monitor('thought', {
                'player': current_player,
                'type': 'analysis',
                'content': {
                    'popup': popup_text,
                    'options_count': len(options),
                    'argent': game_context.get('players', {}).get(current_player, {}).get('money', 0)
                },
                'context': {
                    'tour': game_context.get('global', {}).get('current_turn', 0),
                    'position': game_context.get('players', {}).get(current_player, {}).get('current_space', 'Unknown')
                },
                'timestamp': datetime.utcnow().isoformat()
            }, port=8003)
            
            # Définir le schéma JSON pour la sortie structurée
            schema = {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "description": "Nom exact de l'option choisie",
                        "enum": options if options else ["none"]
                    },
                    "reason": {
                        "type": "string",
                        "description": "Courte explication de la décision (max 30 mots)"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Niveau de confiance entre 0 et 1",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "required": ["decision", "reason", "confidence"],
                "additionalProperties": False
            }

            # Construire le message utilisateur
            user_message = (
                f"Tu es un expert du Monopoly.\n"
                f"Contexte actuel:\n{context_str}\n\n"
                f"Popup: \"{popup_text}\"\n"
                f"Options disponibles: {', '.join(options)}\n\n"
                f"Choisis la meilleure option stratégique."
            )
            
            # Construire la requête complète
            request_data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Tu es un expert Monopoly stratégique. Réponds uniquement en JSON valide."},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "monopoly_decision",
                        "schema": schema,
                        "strict": True
                    }
                },
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            # Afficher la requête JSON complète
            self.logger.info("📡 === REQUÊTE OPENAI ===")
            self.logger.info(f"Model: {model}")
            self.logger.info(f"Messages: {json.dumps(request_data['messages'], indent=2, ensure_ascii=False)}")
            self.logger.info(f"Schema: {json.dumps(schema, indent=2)}")
            self.logger.info("========================")
            
            # Appeler l'API avec Structured Outputs
            response = self.client.chat.completions.create(**request_data)

            # Parser la réponse
            result = json.loads(response.choices[0].message.content)
            
            self.logger.info(f"✅ Décision IA: {result['decision']} - {result['reason']}")
            
            # Envoyer la décision au monitor de chat
            self._send_to_monitor('thought', {
                'player': current_player,
                'type': 'decision',
                'content': {
                    'choix': result['decision'],
                    'raison': result['reason'],
                    'confiance': f"{result.get('confidence', 0.8):.0%}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }, port=8003)
            
            # Envoyer l'action au monitor d'actions
            action_type = self._get_action_type(result['decision'], popup_text)
            self._send_to_monitor('action', {
                'player': current_player,
                'type': action_type,
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': result.get('confidence', 0.8),
                'options': options,
                'timestamp': datetime.utcnow().isoformat()
            }, port=8004)
            
            return {
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': result.get('confidence', 0.8)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur IA: {e}")
            return self._default_decision(options)
    
    def _get_action_type(self, decision: str, popup_text: str) -> str:
        """Détermine le type d'action basé sur la décision et le contexte"""
        decision_lower = decision.lower()
        popup_lower = popup_text.lower()
        
        if 'buy' in decision_lower or 'buy' in popup_lower:
            return 'buy'
        elif 'sell' in decision_lower:
            return 'sell'
        elif 'trade' in decision_lower or 'trade' in popup_lower:
            return 'trade'
        elif 'build' in decision_lower or 'house' in decision_lower or 'hotel' in decision_lower:
            return 'build'
        elif 'roll' in decision_lower or 'dice' in decision_lower:
            return 'roll'
        elif 'jail' in decision_lower or 'jail' in popup_lower:
            return 'jail'
        elif 'chance' in popup_lower or 'community' in popup_lower:
            return 'card'
        elif 'auction' in decision_lower or 'auction' in popup_lower:
            return 'auction'
        elif 'rent' in popup_lower:
            return 'rent'
        elif 'next turn' in decision_lower:
            return 'turn'
        else:
            return 'unknown'
    
    def _format_game_context(self, game_context: Dict) -> str:
        """Formate le contexte du jeu pour l'IA"""
        context_str = ""
        
        # Informations globales
        global_data = game_context.get('global', {})
        context_str += f"Tour: {global_data.get('current_turn', 'N/A')}\n"
        context_str += f"Joueur actuel: {global_data.get('current_player', 'N/A')}\n"
        
        # Informations des joueurs
        players = game_context.get('players', {})
        if players:
            context_str += "\nJoueurs:\n"
            for player_key, player_data in players.items():
                name = player_data.get('name', player_key)
                money = player_data.get('money', 0)
                position = player_data.get('current_space', 'Unknown')
                props = player_data.get('properties', [])
                is_current = "→" if player_data.get('is_current', False) else " "
                in_jail = " (En prison)" if player_data.get('jail', False) else ""
                
                # Informations de base
                context_str += f"{is_current} {name}: ${money}, {len(props)} propriétés, position: {position}{in_jail}\n"
                
                # Liste des propriétés du joueur
                if props:
                    props_by_group = {}
                    for prop in props:
                        group = prop.get('group', 'unknown')
                        if group not in props_by_group:
                            props_by_group[group] = []
                        props_by_group[group].append(prop.get('name', 'Unknown'))
                    
                    context_str += "   Propriétés: "
                    prop_list = []
                    for group, names in props_by_group.items():
                        prop_list.append(f"{group} ({', '.join(names)})")
                    context_str += ", ".join(prop_list) + "\n"
        
        # Propriétés importantes
        properties = global_data.get('properties', [])
        if properties:
            owned_props = [p for p in properties if p.get('owner') is not None]
            context_str += f"\nPropriétés: {len(owned_props)}/{len(properties)} possédées\n"
            
            # Groupes de couleurs
            color_groups = {}
            for prop in properties:
                if prop.get('owner') and prop.get('group'):
                    owner = prop['owner']
                    group = prop['group']
                    if owner not in color_groups:
                        color_groups[owner] = {}
                    if group not in color_groups[owner]:
                        color_groups[owner][group] = 0
                    color_groups[owner][group] += 1
            
            if color_groups:
                context_str += "Monopoles potentiels:\n"
                for owner, groups in color_groups.items():
                    for group, count in groups.items():
                        if count >= 2:  # Au moins 2 propriétés du même groupe
                            context_str += f"  - {owner}: {count} {group}\n"
        
        return context_str
    
    def _get_model_for_player(self, player_id: str) -> str:
        """Détermine quel modèle utiliser pour un joueur"""
        # Vérifier les paramètres personnalisés par joueur
        players_config = self.game_settings.get('players', {})
        if player_id in players_config:
            player_config = players_config[player_id]
            if 'ai_model' in player_config:
                return player_config['ai_model']
        
        # Modèle par défaut
        return self.game_settings.get('game', {}).get('default_model', 'gpt-4o-mini')
    
    def _default_decision(self, options: List[str]) -> Dict:
        """Décision par défaut quand l'IA n'est pas disponible"""
        # Priorité des actions par défaut
        priority_order = [
            'next turn', 'ok', 'continue', 'yes', 
            'buy', 'roll dice', 'pay bail', 'auction'
        ]
        
        # Chercher dans l'ordre de priorité
        for priority in priority_order:
            for option in options:
                if priority in option.lower():
                    return {
                        'decision': option,
                        'reason': 'Décision par défaut (IA non disponible)',
                        'confidence': 0.5
                    }
        
        # Si aucune priorité trouvée, prendre la première option
        if options:
            return {
                'decision': options[0],
                'reason': 'Première option disponible',
                'confidence': 0.3
            }
        
        return {
            'decision': 'none',
            'reason': 'Aucune option disponible',
            'confidence': 0.0
        }

# Instance globale du service (singleton)
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Retourne l'instance singleton du service IA"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance