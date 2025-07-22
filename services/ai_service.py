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
        self.auction_data = None  # Pour stocker les données d'enchère
        
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
            context_str = self._format_game_context(game_context, category)
            
            # Déterminer quel modèle utiliser basé sur le joueur actuel
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            
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
            print('\n -------------------- \n')
            print('\n -------------------- \n')

            print(f"ai_provider_name: {ai_provider_name}")
            is_trade_available = category == 'trade'
            print(f"is_trade_available: {is_trade_available}")
            is_auction_available = category == 'auction'
            print(f"is_auction_available: {is_auction_available}")
            is_property_management_available = category == 'property'
            print(f"is_property_management_available: {is_property_management_available}")
            extra_body = None
            print(f"extra_body: {extra_body}")

            print('\n -------------------- \n')
            print('\n -------------------- \n')
            
            if provider == 'gemini':
                ai_client = self.gemini_client
                structured_output = True
                store_data = False
                ai_provider_name = "Gemini"
                extra_body = {
                    'extra_body': {
                        "google": {
                            "thinking_config": {
                                "thinking_budget": 256
                            }
                        }
                    }
                }
            elif provider == 'anthropic':
                ai_client = self.anthropic_client
                structured_output = False
                store_data = False
                ai_provider_name = "Anthropic"
            
            # Construire les messages pour l'API
            
            talk_to_other_players_message = "A n'importe quel moment tu peux utiliser la decision `talk_to_other_players` pour discuter avec les autres joueurs."
            if is_trade_available:
                talk_to_other_players_message += " Tu dois aussi utiliser la decision `talk_to_other_players` pour initier un échange de propriétés avec les autres joueurs, qui amenera a une négociation et à l'échange final."
            
            if is_auction_available:
                talk_to_other_players_message += " Tu dois utiliser la decision `talk_to_other_players` pour initier l'enchère d'une propriété, qui amenera a une négociation et au prix final / enchère gagnante."
                extended_options = ["talk_to_other_players"]

            if is_property_management_available:
                talk_to_other_players_message += " Tu peux aussi utiliser la decision `manage_property` pour acheter, vendre, hypotéquer, dés-hypotéquer des propriétés."
                extended_options.append("manage_property")
            
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
            system_prompt = f"""Tu es une IA qui joue au Monopoly dans une compétition contre une autre IA. Ton objectif est de GAGNER.

Tu as accés au contexte du jeu entre chaque tour. Et tu dois prendre des décisions en fonctions de tes options.

{talk_to_other_players_message}

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
                
            if extra_body:
                request_data["extra_body"] = extra_body
            
            # Afficher la requête JSON complète
            self.logger.info(f"📡 === REQUÊTE {ai_provider_name} ===")
            self.logger.info(f"Model: {model}")
            self.logger.info(f"Messages: {json.dumps(request_data['messages'], indent=2, ensure_ascii=False)}")
            self.logger.info(f"Schema: {json.dumps(schema, indent=2)}")
            self.logger.info("========================")
            
            # Appeler l'API avec Structured Outputs
            
            response = ai_client.chat.completions.create(**request_data)
            print(f"-------------- \n response {response}")
            # Parser la réponse
            result = json.loads(response.choices[0].message.content)
            
            self._add_to_history(current_player, "user", user_message)
            self._add_to_history(current_player, "assistant", response.choices[0].message.content)

            self.global_chat_messages.append(f"{player_name} : {result['chat_message']}")
            
            # result['decision'] = "talk_to_other_players" #FORCE TO TEST
            # result['decision'] = "manage_property"
            ## Gestion de la conversation avec les autres joueurs
            if result['decision'] == "talk_to_other_players":
                self.logger.info("💬 Début d'une conversation avec les autres joueurs")
                # TODO: Gérer "is_trade_available"                
                result = self._run_conversation_between_players(
                    current_player=current_player,
                    result=result,
                    game_context=game_context,
                    context_str=context_str,
                    is_trade_available = is_trade_available,
                    is_auction_available = is_auction_available
                )
                # Re appeler la fonction make_decision, pour que l'IA puisse prendre une décision en fonction de la conversation
                if not result:
                    return self.make_decision(popup_text, options, game_context,category)
            elif result['decision'] == "manage_property":
                self.logger.info("💬 Début de la gestion de propriétés")
                result = self._run_property_management(
                    current_player=current_player,
                    player_name=player_name,
                    ai_client=ai_client,
                    model=model,
                    game_context=game_context,
                    context_str=context_str,
                    chat_message=result['chat_message'],
                    result=result
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
            
            
            return_data = {
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': float(result.get('confidence', 0.8))
            }

            
            if 'trade_data' in result:
                return_data['trade_data'] = result['trade_data']
            if 'auction_data' in result:
                return_data['auction_data'] = result['auction_data']
            if 'property_management_data' in result:
                return_data['property_management_data'] = result['property_management_data']
            

            return return_data
            
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
    
    def _format_game_context(self, game_context: Dict, category: str) -> str:
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
                                'rent': details.get('rent', {}).get('base', 0) if details.get('type') == 'property' else 'special',
                                'houses': prop.get('houses', 0),
                                'is_mortgaged': prop.get('is_mortgaged', False)
                            }
                            props_by_group[group].append(prop_info)
                    
                    context_str += f"   Propriétés ({len(props)}, valeur totale: ${total_property_value}):\n"
                    
                    for group, group_props in props_by_group.items():
                        prop_descriptions = []
                        for p in group_props:
                            desc = f"{p['name']} (${p['value']}"
                            if p['is_mortgaged']:
                                desc += ", HYPOTHÉQUÉE"
                            elif p['houses'] > 0:
                                if p['houses'] == 5:
                                    desc += ", hôtel"
                                else:
                                    desc += f", {p['houses']} maison{'s' if p['houses'] > 1 else ''}"
                            desc += ")"
                            prop_descriptions.append(desc)
                        context_str += f"     - {group}: {', '.join(prop_descriptions)}\n"
                        
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
        
        if category == "auction":
            # Récupérer la propriété en cours d'enchère
            # Check le current player, et récupérer la position du player qui sera l'enchère en cours
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            current_player_position = players.get(current_player, {}).get('current_space', 'Unknown')
            # Récupérer la propriété en cours d'enchère
            current_property = property_manager.get_property_details(current_player_position)
            context_str += f"\nEnchère en cours:\nPropriété en cours d'enchère: {current_property.get('name', 'Unknown')} (Valeur: ${current_property.get('value', 'Unknown')})\n"
        
        if category == "property":
            # Ajouter des informations détaillées pour la gestion de propriétés
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            current_player_data = players.get(current_player, {})
            current_props = current_player_data.get('properties', [])
            
            if current_props:
                context_str += f"\n🏠 GESTION DE PROPRIÉTÉS - Détails pour {current_player_data.get('name', current_player)}:\n"
                context_str += f"💰 Argent disponible: ${current_player_data.get('money', 0)}\n\n"
                
                # Organiser par groupes avec toutes les infos
                props_by_group = {}
                mortgaged_props = []
                for prop in current_props:
                    if prop.get('is_mortgaged', False):
                        mortgaged_props.append(prop['name'])
                    prop_name = prop.get('name', 'Unknown')
                    group = prop.get('group', 'unknown')
                    house_count = prop.get('houses', 0)
                    is_mortgaged = prop.get('is_mortgaged', False)
                    
                    details = property_manager.get_property_details(prop_name)
                    if details and details.get('type') == 'property':
                        if group not in props_by_group:
                            props_by_group[group] = []
                        
                        props_by_group[group].append({
                            'name': prop_name,
                            'houses': house_count,
                            'mortgaged': is_mortgaged,
                            'details': details
                        })
                
                # Afficher les propriétés hypothéquées en premier s'il y en a
                if mortgaged_props:
                    context_str += f"⚠️ PROPRIÉTÉS HYPOTHÉQUÉES ({len(mortgaged_props)}):\n"
                    for prop_name in mortgaged_props:
                        details = property_manager.get_property_details(prop_name)
                        if details:
                            unmortgage_price = int(details.get('mortgage', 0) * 1.1)
                            context_str += f"   - {prop_name}: coût pour lever l'hypothèque = ${unmortgage_price}\n"
                    context_str += "\n"
                
                # Afficher par groupe avec tous les calculs
                for group, group_props in props_by_group.items():
                    group_size = self._get_group_size(group)
                    is_monopoly = group_size and len(group_props) == group_size
                    
                    context_str += f"📍 Groupe {group.upper()}"
                    if is_monopoly:
                        context_str += " ⭐ MONOPOLE COMPLET"
                    context_str += f" ({len(group_props)}/{group_size or '?'} propriétés):\n"
                    
                    for prop_data in group_props:
                        name = prop_data['name']
                        houses = prop_data['houses']
                        mortgaged = prop_data['mortgaged']
                        details = prop_data['details']
                        
                        context_str += f"\n  🏘️ {name}:\n"
                        context_str += f"     - État: "
                        if mortgaged:
                            context_str += "❌ HYPOTHÉQUÉE"
                        elif houses == 5:
                            context_str += "🏨 HÔTEL"
                        elif houses > 0:
                            context_str += f"🏠 {houses} maison(s)"
                        else:
                            context_str += "✅ Terrain nu"
                        context_str += "\n"
                        
                        # Prix et options
                        house_cost = details.get('houseCost', 0)
                        mortgage_value = details.get('mortgage', 0)
                        
                        if not mortgaged:
                            # Options d'achat (seulement si monopole et pas d'hôtel)
                            if is_monopoly and houses < 5 and house_cost > 0:
                                context_str += f"     - Achat maison: ${house_cost} par maison\n"
                                if houses < 3:
                                    context_str += f"     - Achat set 3 maisons: ${house_cost * 3}\n"
                            
                            # Options de vente
                            if houses > 0 and house_cost > 0:
                                context_str += f"     - Vente maison: ${house_cost // 2} par maison\n"
                                if houses >= 3:
                                    context_str += f"     - Vente set 3 maisons: ${(house_cost * 3) // 2}\n"
                            
                            # Option hypothèque (seulement si pas de maisons)
                            if houses == 0:
                                context_str += f"     - Hypothéquer: ${mortgage_value}\n"
                        else:
                            # Option lever l'hypothèque
                            unmortgage_price = int(mortgage_value * 1.1)
                            context_str += f"     - Lever l'hypothèque: ${unmortgage_price}\n"
                    
                    context_str += "\n"
                
                # Ajouter les propriétés spéciales (gares, services)
                special_props = []
                for prop in current_props:
                    details = property_manager.get_property_details(prop.get('name'))
                    if details and details.get('type') in ['station', 'utility']:
                        special_props.append({
                            'name': prop.get('name'),
                            'type': details.get('type'),
                            'mortgaged': prop.get('mortgaged', False),
                            'mortgage': details.get('mortgage', 0)
                        })
                
                if special_props:
                    context_str += "🚂 PROPRIÉTÉS SPÉCIALES:\n"
                    for prop in special_props:
                        context_str += f"  - {prop['name']} ({prop['type']}): "
                        if prop['mortgaged']:
                            context_str += f"❌ Hypothéquée (lever: ${int(prop['mortgage'] * 1.1)})\n"
                        else:
                            context_str += f"✅ Active (hypothéquer: ${prop['mortgage']})\n"
        
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
        Analyse la conversation entre les deux joueurs et détermine l'accord final de l'échange de propriétés ou d'argent.
        Si les deux joueurs sont d'accord, tu dois retourner le montant d'argent et la liste des propriétés que chacun est prêt à échanger.
        Si les deux joueurs ne sont pas d'accord, tu dois retourner 0 pour le montant d'argent et une liste vide pour les propriétés.
        
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
                                "money": {
                                    "type": "number",
                                    "description": "Montant d'argent que le joueur 1 est prêt à échanger (0 si pas d'argent à échanger)"
                                },
                                "properties": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Liste des propriétés que le joueur 1 est prêt à échanger"
                                }
                            },
                            "required": ["money", "properties"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["offers"],
                    "additionalProperties": False
                },
                "player2": {
                    "type": "object",
                    "properties": {
                        "offers": {
                            "type": "object",
                            "properties": {
                                "money": {
                                    "type": "number",
                                    "description": "Montant d'argent que le joueur 2 est prêt à échanger (0 si pas d'argent à échanger)"
                                },
                                "properties": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Liste des propriétés que le joueur 2 est prêt à échanger"
                                }
                            },
                            "required": ["money", "properties"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["offers"],
                    "additionalProperties": False
                }
            },
            "required": ["player1", "player2"],
            "additionalProperties": False
        }

        response = self.openai_client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation d'échange:\n{chr(10).join(last_messages)}\n\nAnalyse cette conversation et détermine les montants d'argent et les propriétés que chacun est prêt à échanger."}
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

    def _get_ai_auction_decision_json(self, player1_name, player2_name, last_messages):
        """
        Analyse la conversation d'enchère et détermine les montants maximum et le gagnant
        """
        system_prompt = f"""
        Tu dois analyser la conversation d'enchère entre deux joueurs et déterminer:
        1. Le montant maximum que chaque joueur est prêt à payer
        2. Qui est le gagnant de l'enchère
        
        Tu dois retourner un JSON valide avec le schema suivant, aucun texte autre que le JSON.
        
        Contexte:
        - Player1: {player1_name}
        - Player2: {player2_name}
        """

        auction_schema = {
            "type": "object",
            "properties": {
                "player1": {
                    "type": "object",
                    "properties": {
                        "max_bid": {
                            "type": "number",
                            "description": "Montant maximum que le joueur 1 est prêt à payer"
                        }
                    },
                    "required": ["max_bid"],
                    "additionalProperties": False
                },
                "player2": {
                    "type": "object",
                    "properties": {
                        "max_bid": {
                            "type": "number", 
                            "description": "Montant maximum que le joueur 2 est prêt à payer"
                        }
                    },
                    "required": ["max_bid"],
                    "additionalProperties": False
                },
                "winner": {
                    "type": "string",
                    "description": "Le joueur gagnant de l'enchère (player1 ou player2)",
                    "enum": ["player1", "player2"]
                },
                "winning_bid": {
                    "type": "number",
                    "description": "Le montant de l'enchère gagnante"
                }
            },
            "required": ["player1", "player2", "winner", "winning_bid"],
            "additionalProperties": False
        }

        response = self.openai_client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation d'enchère:\n{chr(10).join(last_messages)}\n\nAnalyse cette conversation et détermine les montants maximum et le gagnant."}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "monopoly_auction",
                    "schema": auction_schema,
                    "strict": True
                }
            }
        )
        json_result = json.loads(response.choices[0].message.content)
        return json_result

        
    def _get_property_management_decision_json(self, current_player, game_context, context_str, player_message):
        """
        Détermine la décision de gestion de propriétés
        """
        # Récupérer les propriétés du joueur actuel
        players = game_context.get('players', {})
        current_player_data = players.get(current_player, {})
        player_name = current_player_data.get('name', current_player)
        player_properties = current_player_data.get('properties', [])
        
        # Extraire les noms des propriétés
        property_names = []
        for prop in player_properties:
            if prop.get('name'):
                property_names.append(prop['name'])
        
        # Si le joueur n'a pas de propriétés, retourner un résultat vide
        if not property_names:
            return {
                "decisions": {
                    "properties": []
                }
            }
        
        system_prompt = f"""
        Analyse le message du joueur et détermine les actions à effectuer sur les propriétés du joueur.
        Tu dois retourner un JSON valide avec le schema suivant, aucun texte autre que le JSON.
        
        Le joueur qui effectue la gestion de propriétés est le joueur: {current_player} ({player_name})
        
        
        <game_context>
            {context_str}
        </game_context>
        
        
        Règles importantes:
        
        - Les maisons/hôtels sont construits uniformément sur une propriété, ton JSON de décision doit respecter l'ordre d'achat / vente des maisons/hôtels. Tu dois commencer par les propriétés qui ont le moins de maisons/hôtels pour les achats et les propriétés qui ont le plus de maisons/hôtels pour les ventes.
        - Pour hypotéquer une propriété qui a des maisons/hôtels, tu dois d'abord vendre les maisons/hôtels puis après ça faire l'hypothèque.
        
        L'ordre des "decisions" est important.
        """
        
        property_management_schema = {
            "type": "object",
            "properties": {
                "decisions": {
                    "type": "object",
                    "properties": {
                        "properties": {
                            "type": "array",
                            "description": "Liste des décisions à prendre sur chaque propriété.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "property_name": {
                                        "type": "string",
                                        "description": "Nom de la propriété, choisie parmi la liste des propriétés du joueur.",
                                        "enum": property_names
                                    },
                                    "action": {
                                        "type": "string",
                                        "description": "Type d'action à effectuer sur la propriété.",
                                        "enum": [
                                            "buy_house",
                                            "sell_house",
                                            "mortgage",
                                            "unmortgage"
                                        ]
                                    },
                                    "quantity": {
                                        "type": "number",
                                        "description": "Quantité de maisons/hôtels à acheter ou vendre (uniquement pour buy_house ou sell_house, sinon 1 pour mortgage ou unmortgage).",
                                        "minimum": 1
                                    }
                                },
                                "required": [
                                    "property_name",
                                    "action",
                                    "quantity"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": [
                        "properties"
                    ],
                    "additionalProperties": False
                }
            },
            "required": [
                "decisions"
            ],
            "additionalProperties": False
        }
        
        response = self.openai_client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{player_message}"}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "property_management",
                    "schema": property_management_schema,
                    "strict": True
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content)
        return result

    def _run_property_management(self, current_player, player_name, ai_client, model, game_context, context_str, chat_message, result):
        """
        Gère la gestion de propriétés
        """
        self.logger.info(f"💬 ({current_player} - {player_name}) Début de la gestion de propriétés: {chat_message}")
        
        response = ai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": """
                 Tu es une IA qui joue au Monopoly contre une autre IA. Tu as choisi de gérer tes propriétés, tu dois maintenant expliquer clairement ce que tu veux faire avec tes propriétés.
                 Tu peux construire / vendre / hypotéquer / dés-hypotéquer des propriétés.
                 
                 Les règles à respecter:
                 - Tu peux acheter des maisons/hôtels sur une propriété uniquement si tu possède déjà le groupe de couleur de la propriété.
                 - Tu dois construire uniformément les maisons/hôtels sur une propriété, tu ne peux pas construire 1 maison sur une propriété et 3 maisons sur une autre.
                 - Tu peux hypotéquer une propriété uniquement si elle n'est pas déjà hypotéquée et si il n'y a pas de maisons/hôtels sur la propriété.
                 - Tu peux dés-hypotéquer une propriété uniquement si elle est hypotéquée
                 - Tu dois faire attention a tes ressources, tu ne peux pas acheter de maisons/hôtels si tu n'as pas l'argent nécessaire.
                 
                 
                 Tu es le joueur: {current_player} ({player_name})
                 """},
                {"role": "user", "content": f"""
    <game_context>
        Contexte actuel:
        {context_str}
    </game_context>
    
    <actual_chat_message>
        {player_name}: {chat_message}
    </actual_chat_message>
    """}
            ]
        )
        
        # data_json = json.loads(response.choices[0].message.content)
        ai_message = response.choices[0].message.content
        self.logger.info(f"💬 Message de l'IA pour property management: {ai_message}")
        data_json = self._get_property_management_decision_json(current_player, game_context, context_str, ai_message)
        self.logger.info(f"📊 Résultat property management JSON: {data_json}")
        
        new_result = result.copy()
        new_result['decision'] = 'make_property_management'
        new_result['property_management_data'] = data_json
        return new_result

    def _run_conversation_between_players(self, current_player, result, game_context, context_str, is_trade_available, is_auction_available):
        """
        Gère la boucle de conversation entre deux IA jusqu'à END_CONVERSATION, puis relance la décision.
        Retourne le nouveau résultat de décision.
        """
        # Extract player information
        players = game_context.get('players', {})
        player_configs = {
            "player1": {
                'name': players.get("player1", {}).get('name', "player1"),
                'model': players.get("player1", {}).get('ai_model', "gpt-4o-mini"),
                'provider': players.get("player1", {}).get('provider', "openai")
            },
            "player2": {
                'name': players.get("player2", {}).get('name', "player2"),
                'model': players.get("player2", {}).get('ai_model', "gpt-4o-mini"),
                'provider': players.get("player2", {}).get('provider', "openai")
            }
        }
        
        # Get AI clients for both players
        ai_clients = {}
        for player_id, config in player_configs.items():
            if config['provider'] == "anthropic":
                ai_clients[player_id] = self.anthropic_client
            elif config['provider'] == "gemini":
                ai_clients[player_id] = self.gemini_client
            else:
                ai_clients[player_id] = self.openai_client
        
        # Initialize conversation
        conversation_data = []
        current_player_name = player_configs[current_player]['name']
        player_need_answer = "player2" if current_player == "player1" else "player1"
        
        conversation_data.append(f"{current_player_name} : {result['chat_message']}")
        self.logger.info(f"💬 {current_player_name} : {result['chat_message']}")
        
        # Generate system prompts based on availability
        trade_system_prompt, special_commands = self._get_conversation_prompts(is_trade_available, is_auction_available)
        
        
        while True:
            # Get current player configuration
            current_config = player_configs[player_need_answer]
            ai_client = ai_clients[player_need_answer]
            conversation_messages = '\n'.join(conversation_data)
            
            # Create messages for AI
            messages = [
                {"role": "system", "content": "Tu es une IA qui joue au Monopoly contre une autre IA.\nTu es actuellement en train de discuter avec un autre joueur IA. Essaye de rester court dans tes réponses."},
                {"role": "user", "content": f"""Tu es le joueur {player_need_answer} ({current_config['name']})

    {trade_system_prompt}

    <game_context>
        Contexte actuel:
        {context_str}
    </game_context>

    <conversation>
        Messages de la conversation:
        {conversation_messages}
    </conversation>

    MOTS-CLÉS SPÉCIAUX:
    {special_commands}

    EXEMPLES:
    ✅ Réponse normale: "Je suis intéressé par ta propriété orange. Que veux-tu en échange ?"
    ✅ Terminer: "D'accord, merci pour la discussion. [END_CONVERSATION]"
    ❌ NE PAS FAIRE: "Je suis intéressé par ta propriété. [END_CONVERSATION]"
    """}
            ]
            
            # Get AI response
            response = ai_client.chat.completions.create(
                model=current_config['model'],
                messages=messages,
            )
            conversation_result = response.choices[0].message.content
            conversation_data.append(f"{player_need_answer} : {conversation_result}")
            self.logger.info(f"💬 {player_need_answer} : {conversation_result}")
            
            # Check for conversation end or special commands
            end_result = self._handle_conversation_end(conversation_result, conversation_data, result, player_configs)
            if end_result is not None:
                return end_result
                
            # Switch to other player
            player_need_answer = "player2" if player_need_answer == "player1" else "player1"

    def _get_conversation_prompts(self, is_trade_available, is_auction_available):
        """Helper method to generate system prompts and special commands based on availability."""
        if is_trade_available:
            trade_system_prompt = """
    <TRADE_POSSIBILITIES>
    TU PEUX NEGOCIER DES ECHANGES de propriétés ou/Et d'argent !
    </TRADE_POSSIBILITIES>
    """
            special_commands = """- "[END_CONVERSATION]" : UNIQUEMENT si tu considère que la conversation est vraiment terminée (accord conclu, au revoir échangé, plus rien à négocier)
    - "[INIT_TRADE]" pour déclencher un échange de propriétés après avoir négocié avec l'autre joueur et que les deux joueurs sont d'accord."""
        elif is_auction_available:
            trade_system_prompt = """
        <AUCTION_POSSIBILITIES>
        TU PEUX ENCHERIR SUR LA PROPRIETE ACTUELLEMENT EN ENCHERE! Uniquement de l'argent, le joueur qui propose le plus d'argent gagne l'enchère.
        </AUCTION_POSSIBILITIES>
            """
            special_commands = """- "[END_AUCTION]" pour déclencher la fin de l'enchère quand tu ne veux plus enchérir et que tu laisse ton adversaire gagner l'enchère"""
        else:
            trade_system_prompt = """
    <TRADE_POSSIBILITIES>
    TU N'EST PAS SUR LA FENETRE D'ECHANGE de propriétés ou/et d'argent (qui est dans Accounts > Trade), tu ne peux pas négocier d'échange pendant cette discussion. Mais tu peux discuter avec l'autre IA quand même.
    </TRADE_POSSIBILITIES>
    """
            special_commands = """- "[END_CONVERSATION]" : UNIQUEMENT si tu considère que la conversation est vraiment terminée (accord conclu, au revoir échangé, plus rien à négocier)"""
        
        return trade_system_prompt, special_commands

    def _handle_conversation_end(self, conversation_result, conversation_data, result, player_configs):
        """Helper method to handle conversation end scenarios."""
        end_commands = ["[END_CONVERSATION]", "[INIT_TRADE]", "[END_AUCTION]"]
        
        if not any(cmd in conversation_result for cmd in end_commands):
            return None
        
        conversation_messages = '\n'.join(conversation_data)
        new_user_message = f"""Tu as terminé une conversation avec l'autre joueur.
    <conversation>
        Messages de la conversation:
        {conversation_messages}
    </conversation>
    """
        self._add_to_history("player1", "user", new_user_message)
        self._add_to_history("player2", "user", new_user_message)
        
        if "[INIT_TRADE]" in conversation_result:
            return self._handle_trade_completion(player_configs, conversation_data, result)
        elif "[END_AUCTION]" in conversation_result:
            return self._handle_auction_completion(player_configs, conversation_data, result)
        else:
            return False  # La conversation est terminée (Conversation sans choix)

    def _handle_trade_completion(self, player_configs, conversation_data, result):
        """Helper method to handle trade completion."""
        player1_name = player_configs["player1"]["name"]
        player2_name = player_configs["player2"]["name"]
        
        exchange_result = self._get_ai_trade_decision_json(player1_name, player2_name, conversation_data)
        exchange_result["status"] = "deal"
        
        # Si la liste des propriétés est vide et l'argent à 0 on considère que l'échange n'a pas eu lieu
        if exchange_result["player1"]["offers"]["money"] == 0 and len(exchange_result["player1"]["offers"]["properties"]) == 0:
            exchange_result["status"] = "no_deal"
        
        self.logger.info(f"💬 Échange de propriétés: {exchange_result}")
        
        # Sauvegarder les données du trade pour monitor_centralized
        self.trade_data = exchange_result
        
        # Si un trade a été initié, modifier le résultat
        if hasattr(self, 'trade_data') and self.trade_data:
            new_result = result.copy()
            new_result['decision'] = 'make_trade'
            new_result['trade_data'] = self.trade_data
            # Réinitialiser pour la prochaine fois
            self.trade_data = None
            return new_result
        
        return result

    def _handle_auction_completion(self, player_configs, conversation_data, result):
        """Helper method to handle auction completion."""
        player1_name = player_configs["player1"]["name"]
        player2_name = player_configs["player2"]["name"]
        
        auction_result = self._get_ai_auction_decision_json(player1_name, player2_name, conversation_data)
        self.logger.info(f"💰 Résultat d'enchère: {auction_result}")
        
        # Sauvegarder les données de l'enchère pour monitor_centralized
        self.auction_data = auction_result
        
        # Si une enchère a été complétée, modifier le résultat
        if hasattr(self, 'auction_data') and self.auction_data:
            new_result = result.copy()
            new_result['decision'] = 'make_auction'
            new_result['auction_data'] = self.auction_data
            # Réinitialiser pour la prochaine fois
            self.auction_data = None
            return new_result
        
        return result
# Instance globale du service (singleton)
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Retourne l'instance singleton du service IA"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance