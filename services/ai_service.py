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
from src.utils import property_manager
import random
import re
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

class AIService:
    """Service IA pour prendre des décisions dans Monopoly"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.openai_client = None
        self.gemini_client = None
        self.anthropic_client = None
        self.available = False
        self.game_settings = self._load_game_settings()
        self.player1_history = []
        self.player2_history = []
        self.global_chat_messages = []
        self.max_history_length = 20  # Limite de l'historique (messages user+assistant)
        self.trade_data = None  # Pour stocker les données de trade
        
        # Initialiser OpenAI si la clé est disponible
        openai_api_key = os.getenv('OPENAI_API_KEY')
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if openai_api_key and gemini_api_key and anthropic_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.gemini_client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=gemini_api_key) # On utilise le endpoint compatible OpenAI
                self.anthropic_client = OpenAI(base_url="https://api.anthropic.com/v1/", api_key=anthropic_api_key) # On utilise le endpoint compatible OpenAI
                self.available = True
                self.logger.info("✅ Service IA activé")
            except Exception as e:
                self.logger.error(f"⚠️  Erreur initialisation IA: {e}")
        else:
            self.logger.warning("⚠️  Service IA désactivé (pas de clé API)")
    
    def _get_player_history(self, player_id: str) -> List[Dict]:
        """Récupère l'historique du joueur spécifié"""
        if player_id == "player1":
            return self.player1_history
        elif player_id == "player2":
            return self.player2_history
        else:
            # Pour les joueurs inconnus, retourner un historique vide
            # sans affecter les historiques persistants
            return []
    
    def _add_to_history(self, player_id: str, role: str, content: str):
        """Ajoute un message à l'historique du joueur avec gestion de la taille"""
        if player_id == "player1":
            history = self.player1_history
        elif player_id == "player2":
            history = self.player2_history
        else:
            # Ne pas sauvegarder l'historique pour les joueurs inconnus
            return
        
        # Ajouter le nouveau message
        history.append({"role": role, "content": content})
        
        # Limiter la taille de l'historique (garder les messages les plus récents)
        # On garde toujours un nombre pair de messages pour maintenir user/assistant pairs
        if len(history) > self.max_history_length:
            # Supprimer les plus anciens messages par paires (user + assistant)
            messages_to_remove = len(history) - self.max_history_length
            # S'assurer qu'on supprime un nombre pair pour garder la cohérence
            if messages_to_remove % 2 == 1:
                messages_to_remove += 1
            history[:] = history[messages_to_remove:]
    
    def get_history_stats(self) -> Dict:
        """Retourne des statistiques sur l'historique des joueurs"""
        return {
            'player1_messages': len(self.player1_history),
            'player2_messages': len(self.player2_history),
            'max_length': self.max_history_length,
            'player1_last_interaction': self.player1_history[-1]['content'][:50] + "..." if self.player1_history else "Aucune",
            'player2_last_interaction': self.player2_history[-1]['content'][:50] + "..." if self.player2_history else "Aucune"
        }
    
    def clear_history(self, player_id: str = None):
        """Nettoie l'historique d'un joueur spécifique ou de tous les joueurs"""
        if player_id == "player1" or player_id is None:
            self.player1_history.clear()
            self.logger.info("🧹 Historique player1 nettoyé")
        if player_id == "player2" or player_id is None:
            self.player2_history.clear()
            self.logger.info("🧹 Historique player2 nettoyé")
        if player_id is None:
            self.logger.info("🧹 Tous les historiques nettoyés")
    
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
    
    def make_decision(self, popup_text: str, options: List[str], game_context: Dict, category: str) -> Dict:
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
        if not self.available or not self.openai_client or not self.gemini_client or not self.anthropic_client:
            return self._default_decision(options)
        
        try:
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            
            # Déterminer quel modèle utiliser basé sur le joueur actuel
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            # model = self._get_model_for_player(current_player)
            
            # Envoyer le contexte au monitor d'actions
            self._send_to_monitor('context', game_context, port=8004)
            
            # Récupérer le nom réel du joueur
            player_name = game_context.get('players', {}).get(current_player, {}).get('name', current_player)
            model = game_context.get('players', {}).get(current_player, {}).get('ai_model', "gpt-4.1-mini")
            
            # Envoyer la pensée d'analyse au monitor de chat
            self._send_to_monitor('thought', {
                'player': player_name,
                'type': 'analysis',
                'content': {
                    'popup': popup_text,
                    'options': options,
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
            
            extended_options = options + ["talk_to_other_players"]
            
            schema = {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "description": "Nom exact de l'option choisie",
                        "enum": extended_options if extended_options else ["none"]
                    },
                    "reason": {
                        "type": "string",
                        "description": "Courte explication de la décision (max 30 mots)"
                    },
                    "confidence": {
                        "type": "string",
                        "description": "Niveau de confiance entre 0.0 et 1.0",
                        "enum": ["0.0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0"]
                    },
                    "chat_message": {
                        "type": "string",
                        "description": "Message a envoyer dans le chat global du jeu"
                    }
                },
                "required": ["decision", "reason", "confidence", "chat_message"],
                "additionalProperties": False
            }

            # Construire le message utilisateur
            chat_messages = '\n'.join(self.global_chat_messages)
            user_message = f"""
<game_context>
    Contexte actuel:
    {context_str}
</game_context>

<popup_data>
    Texte du popup: "{popup_text}"
    Options disponibles: {', '.join(extended_options)}
</popup_data>

<chat_global>
    Messages du chat global du jeu:
    {chat_messages}
</chat_global>

Choisis la meilleure option stratégique."""
            
            
            # Récupérer l'historique du joueur (copie pour ne pas affecter l'original)
            player_history = self._get_player_history(current_player).copy()
            
            # Charger les paramètres du joueur pour déterminer le provider
            player_settings = None
            game_settings = self._load_game_settings()
            if game_settings and 'players' in game_settings and current_player in game_settings['players']:
                player_settings = game_settings['players'][current_player]
            
            # Déterminer le provider et le client à utiliser
            provider = game_context.get('players', {}).get(current_player, {}).get('provider', "openai")          
            
            ai_client = self.openai_client
            structured_output = True
            store_data = True
            ai_provider_name = "OpenAI"
            
            if provider == 'gemini':
                ai_client = self.gemini_client
                structured_output = True
                store_data = False
                ai_provider_name = "Gemini"
            elif provider == 'anthropic':
                ai_client = self.anthropic_client
                structured_output = False
                store_data = False
                ai_provider_name = "Anthropic"
            
            # Construire les messages pour l'API
            
            system_prompt = """Tu es une IA qui joue au Monopoly dans une compétition contre une autre IA. Ton objectif est de GAGNER.

Tu as accés au contexte du jeu entre chaque tour. Et tu dois prendre des décisions en fonctions de tes options.

A n'importe quel moment tu peux utiliser la decisions TALK_TO_OTHER_PLAYERS pour discuter avec les autres joueurs.

RÉPONSE OBLIGATOIRE en JSON valide avec :
- "decision" : nom exact de l'option choisie .
- "reason" : explication stratégique concise (max 30 mots)  
- "confidence" : niveau de certitude (0.0 à 1.0)
- "chat_message" : message a envoyer dans le chat global du jeu. Visible par tous les joueurs.
"""
            
            
            if not structured_output:
                system_prompt += "\nRéponds uniquement en JSON valide avec le schema suivant, aucun texte autre que le JSON :\n" + json.dumps(schema, indent=2)
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(player_history)
            messages.append({"role": "user", "content": user_message})

            # Construire la requête complète
            request_data = {
                "model": model,
                "messages": messages
            }
            
            if store_data:
                request_data["store"] = True
                
            if structured_output:
                request_data["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "monopoly_decision",
                        "schema": schema,
                        "strict": True
                    }
                }
            
            # Afficher la requête JSON complète
            self.logger.info(f"📡 === REQUÊTE {ai_provider_name} ===")
            self.logger.info(f"Model: {model}")
            self.logger.info(f"Messages: {json.dumps(request_data['messages'], indent=2, ensure_ascii=False)}")
            self.logger.info(f"Schema: {json.dumps(schema, indent=2)}")
            self.logger.info("========================")
            
            # Appeler l'API avec Structured Outputs
            
            response = ai_client.chat.completions.create(**request_data)
            print(f"-------------- \response {response}")
            # Parser la réponse
            result = json.loads(response.choices[0].message.content)
            
            self._add_to_history(current_player, "user", user_message)
            self._add_to_history(current_player, "assistant", json.dumps(result))

            self.global_chat_messages.append(f"{player_name} : {result['chat_message']}")
            
            #result['decision'] = "talk_to_other_players" #FORCE TO TEST
            ## Gestion de la conversation avec les autres joueurs
            if result['decision'] == "talk_to_other_players":
                self.logger.info("💬 Début d'une conversation avec les autres joueurs")
                # TODO: Gérer "is_trade_available"
                result = self._run_conversation_between_players(
                    current_player=current_player,
                    result=result,
                    game_context=game_context,
                    context_str=context_str,
                    popup_text=popup_text,
                    options=options,
                    user_message=user_message,
                    request_data=request_data,
                    request_ai_client=ai_client,
                    is_trade_available = bool(category == 'trade')
                )

            
            self.logger.info(f"✅ Décision IA: {result['decision']} - {result['reason']}")
            
            # Envoyer la décision au monitor de chat
            self._send_to_monitor('thought', {
                'player': player_name,
                'type': 'decision',
                'content': {
                    'choix': result['decision'],
                    'raison': result['reason'],
                    'confiance': f"{float(result.get('confidence', 0.8)):.0%}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }, port=8003)
            
            # Générer un message de chat selon la décision
            chat_message = result['chat_message']
            if chat_message:
                self._send_to_monitor('chat', {
                    'from': player_name,
                    'to': 'All',
                    'message': chat_message,
                    'timestamp': datetime.utcnow().isoformat()
                }, port=8003)
            
            # Envoyer l'action au monitor d'actions
            action_type = self._get_action_type(result['decision'], popup_text)
            self._send_to_monitor('action', {
                'player': current_player,
                'type': action_type,
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': float(result.get('confidence', 0.8)),
                'options': options,
                'timestamp': datetime.utcnow().isoformat()
            }, port=8004)
            
            return {
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': float(result.get('confidence', 0.8))
            }
            
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            self.logger.error(f"❌ Erreur IA: {e}\nTraceback:\n{tb_str}")
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
                
                # Liste des propriétés du joueur avec détails complets
                if props:
                    props_by_group = {}
                    total_property_value = 0
                    
                    for prop in props:
                        prop_name = prop.get('name', 'Unknown')
                        group = prop.get('group', 'unknown')
                        
                        # Récupérer les détails complets depuis property_manager
                        details = property_manager.get_property_details(prop_name)
                        if details:
                            total_property_value += details.get('value', 0)
                            
                            if group not in props_by_group:
                                props_by_group[group] = []
                            
                            # Créer une description enrichie de la propriété
                            prop_info = {
                                'name': prop_name,
                                'value': details.get('value', 0),
                                'rent': details.get('rent', {}).get('base', 0) if details.get('type') == 'property' else 'special'
                            }
                            props_by_group[group].append(prop_info)
                    
                    context_str += f"   Propriétés ({len(props)}, valeur totale: ${total_property_value}):\n"
                    
                    for group, group_props in props_by_group.items():
                        prop_names = [f"{p['name']} (${ p['value']})" for p in group_props]
                        context_str += f"     - {group}: {', '.join(prop_names)}\n"
                        
                        # Vérifier si le groupe est complet pour un monopole
                        group_size = self._get_group_size(group)
                        if group_size and len(group_props) == group_size:
                            context_str += f"       ⚠️ MONOPOLE COMPLET! Peut construire des maisons.\n"
        
        # Propriétés importantes
        properties = global_data.get('properties', [])
        if properties:
            owned_props = [p for p in properties if p.get('owner') is not None]
            available_props = [p for p in properties if p.get('owner') is None]
            
            context_str += f"\nPropriétés sur le plateau: {len(owned_props)}/{len(properties)} possédées\n"
            
            # Propriétés disponibles à l'achat
            if available_props:
                context_str += f"\nPropriétés disponibles ({len(available_props)}):\n"
                # Grouper par couleur
                available_by_group = {}
                for prop in available_props[:5]:  # Limiter à 5 pour ne pas surcharger
                    group = prop.get('group', 'unknown')
                    if group not in available_by_group:
                        available_by_group[group] = []
                    
                    # Récupérer les détails
                    details = property_manager.get_property_details(prop.get('name'))
                    if details:
                        available_by_group[group].append({
                            'name': prop.get('name'),
                            'value': details.get('value', 0)
                        })
                
                for group, props in available_by_group.items():
                    prop_list = [f"{p['name']} (${p['value']})" for p in props]
                    context_str += f"  - {group}: {', '.join(prop_list)}\n"
            
            # Groupes de couleurs et monopoles
            color_groups = {}
            for prop in properties:
                if prop.get('owner') and prop.get('group'):
                    owner = prop['owner']
                    group = prop['group']
                    if owner not in color_groups:
                        color_groups[owner] = {}
                    if group not in color_groups[owner]:
                        color_groups[owner][group] = []
                    color_groups[owner][group].append(prop.get('name'))
            
            if color_groups:
                context_str += "\nSituation des monopoles:\n"
                for owner, groups in color_groups.items():
                    player_name = self._get_player_name_by_id(owner, players)
                    for group, prop_names in groups.items():
                        group_size = self._get_group_size(group)
                        if group_size:
                            status = "MONOPOLE!" if len(prop_names) == group_size else f"{len(prop_names)}/{group_size}"
                            context_str += f"  - {player_name}: {group} [{status}]\n"
        
        return context_str
    
    def _get_group_size(self, group: str) -> Optional[int]:
        """Retourne le nombre de propriétés dans un groupe de couleur"""
        group_sizes = {
            'brown': 2,
            'light_blue': 3,
            'pink': 3,
            'orange': 3,
            'red': 3,
            'yellow': 3,
            'green': 3,
            'dark_blue': 2,
            'station': 4,
            'utility': 2
        }
        return group_sizes.get(group.lower())
    
    def _get_player_name_by_id(self, player_id: str, players: Dict) -> str:
        """Trouve le nom du joueur par son ID"""
        for player_key, player_data in players.items():
            if player_data.get('id') == player_id or player_key == player_id:
                return player_data.get('name', player_key)
        return player_id
    
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

    def _get_ai_trade_decision_json(self, player1_name, player2_name, last_messages):
        system_prompt = f"""
        Tu dois retourner un JSON valide avec le schema suivant, aucun texte autre que le JSON.
        
        Contexte:
        - Player1: {player1_name}
        - Player2: {player2_name}
        """

        exchange_schema = {
            "type": "object",
            "properties": {
                "player1": {
                    "type": "object",
                    "properties": {
                        "offers": {
                            "type": "object",
                            "properties": {
                                "money": {"type": "number"},
                                "properties": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["money", "properties"]
                        }
                    },
                    "required": ["offers"]
                },
                "player2": {
                    "type": "object",
                    "properties": {
                        "offers": {
                            "type": "object",
                            "properties": {
                                "money": {"type": "number"},
                                "properties": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["money", "properties"]
                        }
                    },
                    "required": ["offers"]
                }
            },
            "required": ["player1", "player2"],
            "additionalProperties": False
        }

        response = self.openai_client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{chr(10).join(last_messages)}"}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "monopoly_trade",
                    "schema": exchange_schema,
                    "strict": True
                }
            }
        )
        json_result = json.loads(response.choices[0].message.content)
        return json_result

    def _run_conversation_between_players(self, current_player, result, game_context, context_str, popup_text, options, user_message, request_ai_client, request_data, is_trade_available):
        """
        Gère la boucle de conversation entre deux IA jusqu'à END_CONVERSATION, puis relance la décision.
        Retourne le nouveau résultat de décision.
        """
        conversation_data = []
        player1_name = game_context.get('players', {}).get("player1", {}).get('name', "player1")
        player2_name = game_context.get('players', {}).get("player2", {}).get('name', "player2")
        player1_model = game_context.get('players', {}).get("player1", {}).get('ai_model', "gpt-4o-mini")
        player2_model = game_context.get('players', {}).get("player2", {}).get('ai_model', "gpt-4o-mini")
        
        player1_provider = game_context.get('players', {}).get("player1", {}).get('provider', "openai")
        player2_provider = game_context.get('players', {}).get("player2", {}).get('provider', "openai")
        
        ai_client_player1 = self.openai_client
        ai_client_player2 = self.openai_client
        
        if player1_provider == "anthropic":
            ai_client_player1 = self.anthropic_client
        elif player1_provider == "gemini":
            ai_client_player1 = self.gemini_client
        
        if player2_provider == "anthropic":
            ai_client_player2 = self.anthropic_client
        elif player2_provider == "gemini":
            ai_client_player2 = self.gemini_client
        
        player_need_answer = "player1"
        if current_player == "player1":
            conversation_data.append(f"{player1_name} : {result['chat_message']}")
            player_need_answer = "player2"
            self.logger.info(f"💬 {player1_name} : {result['chat_message']}")
        else:
            conversation_data.append(f"{player2_name} : {result['chat_message']}")
            player_need_answer = "player1"
            self.logger.info(f"💬 {player2_name} : {result['chat_message']}")
        while True:
            
            ai_client = ai_client_player1 if player_need_answer == "player1" else ai_client_player2
            ai_model = player1_model if player_need_answer == "player1" else player2_model
            conversation_messages = '\n'.join(conversation_data)
            trade_message_system_prompt = "TU N'EST PAS SUR LA FENETRE D'ECHANGE de propriétés ou/et d'argent (qui est dans Accounts > Trade), tu ne peux pas négocier d'échange pendant cette discussion. Mais tu peux discuter avec l'autre IA quand même."
            if is_trade_available:
                trade_message_system_prompt = "TU PEUX NEGOCIER DES ECHANGES de propriétés ou/Et d'argent !"
                trade_message = """
                - "[INIT_TRADE]" pour déclencher un échange de propriétés après avoir négocié avec l'autre joueur et que les deux joueurs sont d'accord.
                """
            else:
                trade_message = ""

            messages = [
                {"role": "system", "content": f"""
Tu es une IA qui joue au Monopoly contre une autre IA.
Tu es actuellement en train de discuter avec un autre joueur IA. Essaye de rester court dans tes réponses.
                """},
                {"role": "user", "content": f"""
Tu es le joueur {player_need_answer} ({player1_name if player_need_answer == "player1" else player2_name})

<TRADE POSSIBILITIES ?>
{trade_message_system_prompt}
</TRADE POSSIBILITIES?>

<game_context>
    Contexte actuel:
    {context_str}
</game_context>

<popup_data>
    Texte du popup: "{popup_text}"
    Options disponibles: {', '.join(options)}
</popup_data>

<conversation>
    Messages de la conversation:
    {conversation_messages}
</conversation>


MOTS-CLÉS SPÉCIAUX:
- "[END_CONVERSATION]" : UNIQUEMENT si tu considère que la conversation est vraiment terminée (accord conclu, au revoir échangé, plus rien à négocier)
{trade_message}

EXEMPLES:
✅ Réponse normale: "Je suis intéressé par ta propriété orange. Que veux-tu en échange ?"
✅ Terminer: "D'accord, merci pour la discussion. [END_CONVERSATION]"
❌ NE PAS FAIRE: "Je suis intéressé par ta propriété. [END_CONVERSATION]"
 """}
            ]
            response = ai_client.chat.completions.create(
                model=ai_model,
                messages=messages,
            )
            conversation_result = response.choices[0].message.content
            conversation_data.append(f"{player_need_answer} : {conversation_result}")
            self.logger.info(f"💬 {player_need_answer} : {conversation_result}")
            if conversation_result.find("[END_CONVERSATION]") != -1 or conversation_result.find("[INIT_TRADE]") != -1:
                if conversation_result.find("[INIT_TRADE]") != -1:
                    # Les IA décident de faire un échange de propriétés
                    exchange_result = self._get_ai_trade_decision_json(player1_name, player2_name, conversation_data)
                    self.logger.info(f"💬 Échange de propriétés: {exchange_result}")
                    # Sauvegarder les données du trade pour monitor_centralized
                    self.trade_data = exchange_result
                    conversation_messages.append(f"[TRADE_COMPLETED]")
                    # Si un trade a été initié, modifier le résultat
                    if hasattr(self, 'trade_data') and self.trade_data:
                        new_result = result
                        new_result['decision'] = 'make_trade'
                        new_result['trade_data'] = self.trade_data
                        # Réinitialiser pour la prochaine fois
                        self.trade_data = None
                    return new_result
                new_request_data = request_data.copy()
                new_request_data['messages'] = list(request_data['messages'])  # copy list
                new_request_data['messages'].append({"role": "user", "content": user_message})
                new_request_data['messages'].append({"role": "assistant", "content": json.dumps(result)})
                new_request_data['messages'].append({"role": "user", "content": f"""Tu as terminé la conversation avec l'autre joueur.
<conversation>
    Messages de la conversation:
    {conversation_messages}
</conversation>

<popup_data>
    Texte du popup: "{popup_text}"
    Options disponibles: {', '.join(options)}
</popup_data>

Répond maintenant à la question du popup."""})
                response = request_ai_client.chat.completions.create(**new_request_data)
                # Parser la réponse
                try:
                    new_result = json.loads(response.choices[0].message.content)
                except Exception as e:
                    self.logger.error(f"Erreur parsing JSON après conversation: {e}")
                    new_result = result  # fallback
                self._add_to_history(current_player, "user", user_message)
                self._add_to_history(current_player, "assistant", json.dumps(new_result))
                
                # Si un trade a été initié, modifier le résultat
                if hasattr(self, 'trade_data') and self.trade_data:
                    new_result['decision'] = 'make_trade'
                    new_result['trade_data'] = self.trade_data
                    # Réinitialiser pour la prochaine fois
                    self.trade_data = None
                return new_result
            # Alterner le joueur qui doit répondre
            player_need_answer = "player2" if player_need_answer == "player1" else "player1"

# Instance globale du service (singleton)
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Retourne l'instance singleton du service IA"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance