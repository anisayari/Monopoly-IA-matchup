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
        self.max_history_length = 20  # Limite de l'historique (messages user+assistant)
        
        # Initialiser OpenAI si la clé est disponible
        openai_api_key = os.getenv('OPENAI_API_KEY')
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Log des clés trouvées
        print("[AI Service] Checking API keys...")
        print(f"[AI Service] OpenAI key: {'✅ Found' if openai_api_key else '❌ Not found'}")
        print(f"[AI Service] Gemini key: {'✅ Found' if gemini_api_key else '❌ Not found'}")
        print(f"[AI Service] Anthropic key: {'✅ Found' if anthropic_api_key else '❌ Not found'}")
        
        if openai_api_key and gemini_api_key and anthropic_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.gemini_client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=gemini_api_key) # On utilise le endpoint compatible OpenAI
                self.anthropic_client = OpenAI(base_url="https://api.anthropic.com/v1/", api_key=anthropic_api_key) # On utilise le endpoint compatible OpenAI
                self.available = True
                self.logger.info("✅ Service IA activé")
                print("[AI Service] ✅ All AI providers initialized successfully")
            except Exception as e:
                self.logger.error(f"⚠️  Erreur initialisation IA: {e}")
                print(f"[AI Service] ❌ Error initializing AI providers: {e}")
        else:
            self.logger.warning("⚠️  Service IA désactivé (pas de clé API)")
            print("[AI Service] ⚠️  AI Service disabled - missing API key(s)")
    
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
            response = requests.post(url, json=data, timeout=1)
            if port == 8003:  # Log for chat monitor
                print(f"[AI Chat] Sent {endpoint} for {data.get('player', data.get('from', 'Unknown'))}")
        except requests.exceptions.ConnectionError:
            if port == 8003:
                print(f"[AI Chat] Monitor not running on port {port}")
        except Exception as e:
            if port == 8003:
                print(f"[AI Chat] Error sending to monitor: {e}")
    
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
        
        # Log pour debug
        current_player = game_context.get('global', {}).get('current_player', 'Unknown')
        player_name = game_context.get('players', {}).get(current_player, {}).get('name', current_player)
        print(f"\n[AI Service] Decision requested for {player_name}")
        print(f"[AI Service] Popup: {popup_text[:50]}...")
        print(f"[AI Service] Options: {options}")
        
        # Si l'IA n'est pas disponible, utiliser la logique par défaut
        if not self.available or not self.openai_client or not self.gemini_client or not self.anthropic_client:
            print(f"[AI Service] AI not available, using default decision")
            return self._default_decision(options)
        
        try:
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            
            # Déterminer quel modèle utiliser basé sur le joueur actuel
            current_player = game_context.get('global', {}).get('current_player', 'Unknown')
            model = self._get_model_for_player(current_player)
            
            # Envoyer le contexte au monitor d'actions
            self._send_to_monitor('context', game_context, port=8004)
            
            # Récupérer le nom réel du joueur
            player_name = game_context.get('players', {}).get(current_player, {}).get('name', current_player)
            
            # Envoyer la pensée d'analyse au monitor de chat
            self._send_to_monitor('thought', {
                'player': player_name,
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
            
            # Ajouter l'option de parler aux autres IA si ce n'est pas déjà inclus
            extended_options = options.copy() if options else []
            if "talk_to_other_ai" not in [opt.lower() for opt in extended_options]:
                extended_options.append("talk_to_other_ai")
            
            # Définir le schéma JSON pour la sortie structurée
            schema = {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "description": "Nom exact de l'option choisie (ou 'talk_to_other_ai' pour discuter d'abord)",
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
                    }
                },
                "required": ["decision", "reason", "confidence"],
                "additionalProperties": False
            }

            # Construire le message utilisateur
            user_message = (
                f"Contexte actuel:\n{context_str}\n\n"
                f"Popup: \"{popup_text}\"\n"
                f"Options disponibles: {', '.join(options)}\n\n"
                f"Choisis la meilleure option stratégique."
            )
            
            
            # Récupérer l'historique du joueur (copie pour ne pas affecter l'original)
            player_history = self._get_player_history(current_player).copy()
            
            # Charger les paramètres du joueur pour déterminer le provider
            player_settings = None
            game_settings = self._load_game_settings()
            if game_settings and 'players' in game_settings and current_player in game_settings['players']:
                player_settings = game_settings['players'][current_player]
            
            # Déterminer le provider et le client à utiliser
            provider = player_settings.get('provider', 'openai') if player_settings else 'openai'
            
            ai_client = self.openai_client
            structured_output = True
            store_data = True
            ai_provider_name = "OpenAI"
            
            if provider == 'gemini' or model.startswith("gemini"):
                ai_client = self.gemini_client
                structured_output = True
                store_data = False
                ai_provider_name = "Gemini"
            elif provider == 'anthropic' or model.startswith("claude"):
                ai_client = self.anthropic_client
                structured_output = False
                store_data = False
                ai_provider_name = "Anthropic"
            
            # Construire les messages pour l'API
            
            system_prompt = """Tu es une IA experte au Monopoly dans une compétition contre d'autres IA. Ton objectif est de GAGNER en maximisant tes profits et en ruinant tes adversaires.

STRATÉGIES PRIORITAIRES :
• MONOPOLES : Acquérir des groupes de couleur complets pour construire des maisons/hôtels = revenus massifs
• LIQUIDITÉS : Maintenir un cash flow positif pour saisir les opportunités et payer les loyers
• POSITION : Contrôler les propriétés les plus rentables (orange, rouge, jaune = zones à fort trafic)
• ÉCHANGES : Négocier intelligemment pour compléter tes monopoles, même à perte temporaire
• TIMING : Acheter agressivement en début de partie, construire massivement dès le premier monopole
• COMMUNICATION : Tu peux choisir 'talk_to_other_ai' pour discuter avec ton adversaire avant de prendre une décision importante

ANALYSE CONTEXTUELLE requise :
• Argent disponible vs coûts futurs probables
• Propriétés des adversaires et leurs stratégies de monopole  
• Position sur le plateau et probabilités de mouvement
• Phase de jeu (début = acheter, milieu = monopoliser, fin = optimiser)

NOTE: Si tu choisis 'talk_to_other_ai', tu pourras engager une conversation stratégique avec l'autre IA avant de prendre ta décision finale.

DÉCISIONS TYPES :
• ACHAT : Toujours acheter sauf si cela compromet ta liquidité critique
• ENCHÈRES : Évaluer la valeur stratégique vs prix, empêcher les monopoles adverses
• CONSTRUCTION : Construire massivement dès le premier monopole complet
• PRISON : Rester en prison tard dans la partie pour éviter les loyers élevés
• ÉCHANGES : Accepter des pertes à court terme pour des gains stratégiques à long terme

RÉPONSE OBLIGATOIRE en JSON valide avec :
- "decision" : nom exact de l'option choisie
- "reason" : explication stratégique concise (max 30 mots)  
- "confidence" : niveau de certitude (0.0 à 1.0)

ANALYSE → STRATÉGIE → DÉCISION. Sois impitoyable et calculateur."""
            
            
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
                "messages": messages,
                "max_tokens": 500
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

            # Parser la réponse
            result = json.loads(response.choices[0].message.content)
            
            self._add_to_history(current_player, "user", user_message)
            self._add_to_history(current_player, "assistant", result)
            
            self.logger.info(f"✅ Décision IA: {result['decision']} - {result['reason']}")
            
            # Boucle pour gérer les conversations multiples
            conversation_count = 0
            max_conversations = 3  # Limite pour éviter les boucles infinies
            
            while result['decision'].lower() == 'talk_to_other_ai' and conversation_count < max_conversations:
                conversation_count += 1
                self.logger.info(f"🗣️ {player_name} veut discuter avec l'autre IA (conversation {conversation_count})")
                
                # Initier une conversation
                conversation_result = self._initiate_ai_conversation(
                    initiator_player=current_player,
                    initiator_name=player_name,
                    popup_text=popup_text,
                    options=options,
                    game_context=game_context,
                    initial_reason=result['reason'],
                    conversation_round=conversation_count
                )
                
                # Si la conversation retourne une décision finale, on sort de la boucle
                if conversation_result['decision'].lower() != 'talk_to_other_ai':
                    return conversation_result
                
                # Sinon, on continue avec le nouveau résultat
                result = conversation_result
            
            # Si on a atteint la limite de conversations, forcer une décision
            if conversation_count >= max_conversations:
                self.logger.warning(f"⚠️ Limite de conversations atteinte, forçant une décision")
                # Refaire l'appel sans l'option talk_to_other_ai
                final_options = [opt for opt in options if opt.lower() != 'talk_to_other_ai']
                return self._make_final_decision_after_conversation(
                    player=current_player,
                    player_name=player_name,
                    popup_text=popup_text,
                    options=final_options,
                    game_context=game_context,
                    conversation_history=[]
                )
            
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
            chat_message = self._generate_chat_message(result['decision'], popup_text, game_context, player_name)
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
            self.logger.error(f"❌ Erreur IA: {e}")
            return self._default_decision(options)
    
    def _generate_chat_message(self, decision: str, popup_text: str, game_context: Dict, player_name: str) -> Optional[str]:
        """Génère un message de chat basé sur la décision prise"""
        decision_lower = decision.lower()
        popup_lower = popup_text.lower()
        
        # Si l'IA veut parler aux autres
        if decision_lower == 'talk_to_other_ai':
            messages = [
                "J'aimerais discuter de cette décision avec vous.",
                "Avant de décider, parlons-en ensemble.",
                "Je pense qu'une discussion s'impose ici.",
                "Qu'est-ce que vous en pensez, les amis?"
            ]
            return random.choice(messages)
        
        # Messages selon le type de décision
        if 'buy' in decision_lower and 'buy' in popup_lower:
            property_match = re.search(r'buy\s+(.+?)\s+for', popup_text, re.IGNORECASE)
            if property_match:
                property_name = property_match.group(1)
                messages = [
                    f"Je prends {property_name}! 🏠",
                    f"Excellente acquisition avec {property_name}!",
                    f"{property_name} sera rentable à long terme.",
                    f"Un pas de plus vers la victoire avec {property_name}!"
                ]
                return random.choice(messages)
        
        elif 'auction' in decision_lower:
            messages = [
                "Voyons qui va remporter cette enchère...",
                "Je passe mon tour sur les enchères.",
                "Laissons les autres se battre pour ça.",
                "Les enchères ne m'intéressent pas cette fois."
            ]
            return random.choice(messages)
        
        elif 'trade' in decision_lower:
            messages = [
                "Intéressant... Voyons ce trade.",
                "Hmm, cette offre mérite réflexion.",
                "Je vais analyser cette proposition.",
                "Un échange pourrait être profitable..."
            ]
            return random.choice(messages)
        
        elif 'next turn' in decision_lower:
            messages = [
                "Au suivant! 🎲",
                "C'est parti pour le prochain tour!",
                "Voyons ce que les dés nous réservent...",
                "J'ai hâte de voir la suite!"
            ]
            return random.choice(messages)
        
        elif 'roll' in decision_lower:
            if 'jail' in popup_lower:
                messages = [
                    "Je tente ma chance avec les dés! 🎲🎲",
                    "Allez, double pour sortir!",
                    "Les dés vont me libérer!",
                    "Je mise sur un double!"
                ]
            else:
                messages = [
                    "C'est parti! 🎲",
                    "Lançons les dés!",
                    "Voyons où je vais atterrir...",
                    "Les dés sont lancés!"
                ]
            return random.choice(messages)
        
        elif 'pay' in decision_lower and 'bail' in decision_lower:
            messages = [
                "Je préfère payer et sortir rapidement.",
                "50€ pour la liberté, c'est raisonnable.",
                "Pas le temps de rester en prison!",
                "Je paie la caution et je continue!"
            ]
            return random.choice(messages)
        
        # Si c'est une propriété qu'on possède déjà
        if 'already own' in popup_lower:
            messages = [
                "Ah, je suis chez moi ici! 😊",
                "Toujours agréable de visiter ses propriétés.",
                "Ma propriété me protège!",
                "Home sweet home!"
            ]
            return random.choice(messages)
        
        return None
    
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
    
    def _initiate_ai_conversation(self, initiator_player: str, initiator_name: str, popup_text: str, 
                                   options: List[str], game_context: Dict, initial_reason: str, 
                                   conversation_round: int = 1) -> Dict:
        """Initie une conversation entre les deux IA"""
        try:
            # Déterminer l'autre joueur
            other_player = "player2" if initiator_player == "player1" else "player1"
            other_name = game_context.get('players', {}).get(other_player, {}).get('name', other_player)
            
            # Message d'ouverture différent selon le round
            if conversation_round == 1:
                opening_message = f"Hé {other_name}, j'aimerais discuter avant de prendre ma décision. {initial_reason}"
            else:
                opening_message = f"{other_name}, j'ai encore besoin de discuter. {initial_reason}"
            
            # Envoyer le début de conversation au monitor
            self._send_to_monitor('chat', {
                'from': initiator_name,
                'to': other_name,
                'message': opening_message,
                'timestamp': datetime.utcnow().isoformat()
            }, port=8003)
            
            # Conversation dynamique (2-4 échanges)
            conversation_history = []
            exchanges = random.randint(2, 4)
            
            for round in range(exchanges):
                # L'autre IA répond
                other_response = self._generate_ai_response(
                    responder_player=other_player,
                    responder_name=other_name,
                    conversation_context=conversation_history,
                    game_context=game_context,
                    initiator_message=initial_reason if round == 0 else conversation_history[-1]['message']
                )
                
                conversation_history.append({
                    'from': other_name,
                    'to': initiator_name,
                    'message': other_response
                })
                
                self._send_to_monitor('chat', {
                    'from': other_name,
                    'to': initiator_name,
                    'message': other_response,
                    'timestamp': datetime.utcnow().isoformat()
                }, port=8003)
                
                # L'initiateur répond (sauf au dernier tour)
                if round < exchanges - 1:
                    initiator_response = self._generate_ai_response(
                        responder_player=initiator_player,
                        responder_name=initiator_name,
                        conversation_context=conversation_history,
                        game_context=game_context,
                        initiator_message=other_response
                    )
                    
                    conversation_history.append({
                        'from': initiator_name,
                        'to': other_name,
                        'message': initiator_response
                    })
                    
                    self._send_to_monitor('chat', {
                        'from': initiator_name,
                        'to': other_name,
                        'message': initiator_response,
                        'timestamp': datetime.utcnow().isoformat()
                    }, port=8003)
            
            # Décider si on continue la conversation ou si on prend une décision
            # Plus on a eu de conversations, plus on a tendance à prendre une décision
            continue_talking_probability = max(0.1, 0.7 - (conversation_round * 0.2))
            
            if random.random() < continue_talking_probability:
                # Continuer la conversation
                self._send_to_monitor('chat', {
                    'from': initiator_name,
                    'to': 'All',
                    'message': "Hmm, j'ai encore besoin de réfléchir avec vous...",
                    'timestamp': datetime.utcnow().isoformat()
                }, port=8003)
                
                return {
                    'decision': 'talk_to_other_ai',
                    'reason': f"J'ai besoin de continuer la discussion après {exchanges} échanges",
                    'confidence': 0.5
                }
            else:
                # Prendre une décision finale
                self._send_to_monitor('chat', {
                    'from': initiator_name,
                    'to': 'All',
                    'message': "Bon, après cette discussion enrichissante, voici ma décision...",
                    'timestamp': datetime.utcnow().isoformat()
                }, port=8003)
                
                # Refaire l'appel de décision mais sans l'option talk_to_other_ai
                final_options = [opt for opt in options if opt.lower() != 'talk_to_other_ai']
                return self._make_final_decision_after_conversation(
                    player=initiator_player,
                    player_name=initiator_name,
                    popup_text=popup_text,
                    options=final_options,
                    game_context=game_context,
                    conversation_history=conversation_history
                )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la conversation IA: {e}")
            # Fallback: prendre une décision normale
            return self._default_decision(options)
    
    def _generate_ai_response(self, responder_player: str, responder_name: str, 
                             conversation_context: List[Dict], game_context: Dict, 
                             initiator_message: str) -> str:
        """Génère une réponse d'IA dans une conversation"""
        try:
            # Déterminer le modèle pour ce joueur
            model = self._get_model_for_player(responder_player)
            
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            
            # Construire l'historique de conversation
            conv_history = "\n".join([f"{msg['from']}: {msg['message']}" for msg in conversation_context])
            
            # Message système pour la conversation
            system_msg = f"""Tu es {responder_name}, une IA jouant au Monopoly. 
Un autre joueur IA t'a contacté pour discuter de stratégie.
Réponds de manière stratégique et concise (max 2 phrases).
Considère tes propres intérêts tout en restant diplomatique."""
            
            # Construire la requête
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Contexte du jeu:\n{context_str}\n\nHistorique de conversation:\n{conv_history}\n\nDernier message: {initiator_message}\n\nTa réponse:"}
            ]
            
            # Déterminer le client AI
            provider = self.game_settings.get('players', {}).get(responder_player, {}).get('provider', 'openai')
            ai_client = self.openai_client
            if provider == 'gemini':
                ai_client = self.gemini_client
            elif provider == 'anthropic':
                ai_client = self.anthropic_client
            
            # Appeler l'API
            response = ai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Erreur génération réponse IA: {e}")
            # Réponses par défaut
            default_responses = [
                "Intéressant... Je vais y réfléchir.",
                "Je comprends ta position, mais j'ai mes propres priorités.",
                "Hmm, c'est une proposition à considérer.",
                "Je préfère garder ma stratégie pour moi."
            ]
            return random.choice(default_responses)
    
    def _make_final_decision_after_conversation(self, player: str, player_name: str, 
                                               popup_text: str, options: List[str], 
                                               game_context: Dict, conversation_history: List[Dict]) -> Dict:
        """Prend une décision finale après une conversation"""
        try:
            # Préparer le contexte avec l'historique de conversation
            context_str = self._format_game_context(game_context)
            conv_summary = "\n".join([f"{msg['from']}: {msg['message']}" for msg in conversation_history[-3:]])
            
            # Message enrichi avec la conversation
            enhanced_user_message = (
                f"Contexte actuel:\n{context_str}\n\n"
                f"Conversation récente avec l'autre IA:\n{conv_summary}\n\n"
                f"Popup: \"{popup_text}\"\n"
                f"Options disponibles: {', '.join(options)}\n\n"
                f"En tenant compte de cette conversation, choisis la meilleure option stratégique."
            )
            
            # Utiliser le même processus de décision mais avec le contexte enrichi
            model = self._get_model_for_player(player)
            
            # Schéma pour la décision finale (sans talk_to_other_ai)
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
                        "description": "Courte explication de la décision après discussion (max 30 mots)"
                    },
                    "confidence": {
                        "type": "string",
                        "description": "Niveau de confiance entre 0.0 et 1.0",
                        "enum": ["0.0", "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0"]
                    }
                },
                "required": ["decision", "reason", "confidence"],
                "additionalProperties": False
            }
            
            # Déterminer le provider et client
            provider = self.game_settings.get('players', {}).get(player, {}).get('provider', 'openai')
            ai_client = self.openai_client
            structured_output = True
            
            if provider == 'gemini':
                ai_client = self.gemini_client
            elif provider == 'anthropic':
                ai_client = self.anthropic_client
                structured_output = False
            
            # Construire la requête
            messages = [
                {"role": "system", "content": "Tu es une IA experte au Monopoly. Tu viens de discuter avec l'autre IA et dois maintenant prendre une décision finale."},
                {"role": "user", "content": enhanced_user_message}
            ]
            
            request_data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200
            }
            
            if structured_output:
                request_data["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "monopoly_decision",
                        "schema": schema,
                        "strict": True
                    }
                }
            
            # Appeler l'API
            response = ai_client.chat.completions.create(**request_data)
            result = json.loads(response.choices[0].message.content)
            
            # Logging et monitoring
            self.logger.info(f"✅ Décision finale après discussion: {result['decision']} - {result['reason']}")
            
            self._send_to_monitor('thought', {
                'player': player_name,
                'type': 'decision',
                'content': {
                    'choix': result['decision'],
                    'raison': f"Après discussion: {result['reason']}",
                    'confiance': f"{float(result.get('confidence', 0.8)):.0%}"
                },
                'timestamp': datetime.utcnow().isoformat()
            }, port=8003)
            
            return {
                'decision': result['decision'],
                'reason': result['reason'],
                'confidence': float(result.get('confidence', 0.8))
            }
            
        except Exception as e:
            self.logger.error(f"Erreur décision finale: {e}")
            return self._default_decision(options)
    
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

# Instance globale du service (singleton)
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Retourne l'instance singleton du service IA"""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance