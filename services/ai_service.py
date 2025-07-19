"""
Service IA centralisé pour les décisions de jeu
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Dict, List, Optional
from openai import OpenAI
from services.event_bus import EventBus, EventTypes

class AIService:
    """Service IA pour prendre des décisions dans Monopoly"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.client = None
        self.available = False
        self.game_settings = self._load_game_settings()
        
        # Initialiser OpenAI si la clé est disponible
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.available = True
                print("✅ Service IA activé")
            except Exception as e:
                print(f"⚠️  Erreur initialisation IA: {e}")
        else:
            print("⚠️  Service IA désactivé (pas de clé API)")
        
        # S'abonner aux demandes de décision
        self.event_bus.subscribe(EventTypes.AI_DECISION_REQUESTED, self._on_decision_requested)
        # S'abonner aux mises à jour des paramètres du jeu
        self.event_bus.subscribe('game_settings.updated', self._on_game_settings_updated)
    
    def _on_decision_requested(self, event: dict):
        """Callback quand une décision est demandée"""
        data = event['data']
        popup_id = data.get('popup_id')
        popup_text = data.get('popup_text')
        options = data.get('options', [])
        game_context = data.get('game_context', {})
        
        # Prendre la décision
        decision = self.make_decision(popup_text, options, game_context)
        
        # Publier le résultat
        self.event_bus.publish(
            EventTypes.AI_DECISION_MADE,
            {
                'popup_id': popup_id,
                'decision': decision['choice'],
                'reason': decision['reason'],
                'confidence': decision['confidence']
            },
            source='ai_service'
        )
    
    def make_decision(self, popup_text: str, options: List[Dict], game_context: Dict) -> Dict:
        """Prend une décision basée sur le contexte"""
        
        # Si l'IA n'est pas disponible, utiliser la logique par défaut
        if not self.available or not self.client:
            return self._default_decision(options)
        
        try:
            # Extraire les noms des options
            option_names = [opt.get('name', '') for opt in options]
            print(f"🤖 Options disponibles: {option_names}")
            
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            print(f"🤖 Contexte: {context_str}")
            
            # Déterminer quel modèle utiliser basé sur le joueur actuel
            current_player = self._get_current_player_from_context(game_context)
            print(f"🤖 Joueur actuel: {current_player}")
            model = self._get_model_for_player(current_player)
            
            # Obtenir le nom du joueur
            player_name = self._get_player_name(current_player, game_context)
            print(f"🤖 Nom du joueur: {player_name}")
            
            # Définir le schéma JSON pour la sortie structurée
            schema = {
                "type": "object",
                "properties": {
                    "choice": {
                        "type": "string",
                        "description": "Nom exact de l'option choisie",
                        "enum": option_names
                    },
                    "reason": {
                        "type": "string",
                        "description": "Courte explication (max 20 mots)"
                    },
                    "confidence": {
                        "type": "string",
                        "description": "Score de confiance entre 0.0 et 1.0"
                    },
                    "chat_message": {
                        "type": "string",
                        "description": "Un message à envoyer dans le chat, sera visible par tous les autres joueurs"

                    }
                },
                "required": ["choice", "reason", "confidence", "chat_message"],
                "additionalProperties": False
            }

            # Construire le message utilisateur
            user_message = (
                f"Tu es un expert du Monopoly.\n"
                f"Contexte actuel:\n{context_str}\n\n"
                f"Popup: \"{popup_text}\"\n"
                f"Options disponibles: {', '.join(option_names)}\n\n"
            )

            # Publier que l'IA réfléchit
            self.event_bus.publish('ai.thought', {
                'player': player_name,
                'thought': f"Analyse de la situation: {popup_text[:50]}..."
            }, source='ai_service')
            
            # Appeler l'API avec Structured Outputs
            print(f"📡 Appel API OpenAI pour {player_name} avec le modèle {model}")
            response = self.client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": "Expert Monopoly. Réponds uniquement avec un JSON valide conforme au schéma."},
                    {"role": "user", "content": user_message}
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "monopoly_decision",
                        "schema": schema,
                        "strict": True
                    }
                },
                max_output_tokens=1000
            )

            # Vérifier le statut de la réponse
            if response.status != "completed":
                print(f"⚠️  Réponse incomplète: {response.status}")
                if hasattr(response, 'incomplete_details'):
                    print(f"    Raison: {response.incomplete_details.reason if hasattr(response.incomplete_details, 'reason') else response.incomplete_details}")
                return self._default_decision(options)

            # Vérifier s'il y a un refus
            if response.output and len(response.output) > 0:
                first_output = response.output[0]
                if hasattr(first_output, 'content') and len(first_output.content) > 0:
                    first_content = first_output.content[0]
                    if hasattr(first_content, 'type') and first_content.type == "refusal":
                        print(f"⚠️  L'IA a refusé de répondre: {getattr(first_content, 'refusal', 'Refus sans explication')}")
                        return self._default_decision(options)

            # Extraire la réponse JSON
            result_json_str = response.output_text
            print(f"✅ Réponse reçue: {result_json_str}")

            data = json.loads(result_json_str)

            choice = str(data.get("choice", "")).lower()
            reason = data.get("reason", "Décision stratégique")
            confidence = float(data.get("confidence", 0.9))
            chat_message = data.get("chat_message", "")

            # Publier le message de chat si présent
            if chat_message:
                self.event_bus.publish('ai.chat_message', {
                    'player': player_name,
                    'message': chat_message
                }, source='ai_service')
            
            # Publier la pensée sur la décision
            self.event_bus.publish('ai.thought', {
                'player': player_name,
                'thought': f"J'ai décidé: {choice} (confiance: {confidence:.0%}) - {reason}"
            }, source='ai_service')

            # Vérifier que le choix est valide
            if choice not in option_names:
                print(f"⚠️  IA a choisi '{choice}' qui n'est pas dans les options")
                return self._default_decision(options)
            
            return {
                'choice': choice,
                'reason': reason,
                'confidence': confidence
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Erreur IA - JSON invalide: {e}")
            print(f"    Réponse reçue: {result_json_str if 'result_json_str' in locals() else 'Non disponible'}")
            return self._default_decision(options)
        except AttributeError as e:
            print(f"⚠️  Erreur IA - Attribut manquant: {e}")
            print(f"    Vérifiez la structure de la réponse API")
            return self._default_decision(options)
        except Exception as e:
            print(f"⚠️  Erreur IA - {type(e).__name__}: {e}")
            import traceback
            print(f"    Traceback: {traceback.format_exc()}")
            return self._default_decision(options)
    
    def _default_decision(self, options: List[Dict]) -> Dict:
        """Logique de décision par défaut"""
        priority_order = ["buy", "next turn", "roll again", "auction", "trade", "back", "accounts"]
        option_names = [opt.get('name', '') for opt in options]
        
        for priority in priority_order:
            if priority in option_names:
                return {
                    'choice': priority,
                    'reason': 'Priorité par défaut',
                    'confidence': 0.5
                }
        
        # Si aucune priorité, prendre la première option
        if options:
            return {
                'choice': options[0].get('name', 'unknown'),
                'reason': 'Première option disponible',
                'confidence': 0.3
            }
        
        return {
            'choice': 'none',
            'reason': 'Aucune option disponible',
            'confidence': 0.0
        }
    
    def _format_game_context(self, context: Dict) -> str:
        """Formate le contexte du jeu pour l'IA"""
        lines = []
        
        # Joueurs
        if "players" in context:
            lines.append("Joueurs:")
            for player_id, player in context["players"].items():
                name = player.get('name', 'Inconnu')
                money = player.get('money', 0)
                position = player.get('position', 0)
                lines.append(f"- {name}: {money}€, case {position}")
        
        # Tour actuel
        if "global" in context:
            turn = context["global"].get("current_turn", 0)
            lines.append(f"\nTour: {turn}")
        
        return "\n".join(lines)
    
    def _load_game_settings(self) -> Dict:
        """Charge les paramètres du jeu depuis le fichier de configuration"""
        try:
            settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'game_settings.json')
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  Erreur chargement game_settings.json: {e}")
        
        # Paramètres par défaut
        return {
            "players": {
                "player1": {"name": "GPT1", "model": "gpt-4.1-mini", "enabled": True},
                "player2": {"name": "GPT2", "model": "gpt-4.1-mini", "enabled": True}
            },
            "game": {"default_model": "gpt-4.1-mini"}
        }
    
    def _on_game_settings_updated(self, event: dict):
        """Met à jour les paramètres du jeu quand ils changent"""
        self.game_settings = self._load_game_settings()
        print(f"✅ Paramètres du jeu mis à jour")
    
    def _get_current_player_from_context(self, game_context: Dict) -> Optional[str]:
        """Détermine quel joueur est en train de jouer depuis le contexte"""
        # Chercher dans le contexte global
        if "global" in game_context:
            current_player = game_context["global"].get("current_player")
            if current_player:
                return str(current_player)
        
        # Chercher le joueur actif dans la liste des joueurs
        if "players" in game_context:
            for player_id, player_data in game_context["players"].items():
                if player_data.get("is_current", False) or player_data.get("active", False):
                    return player_id
        
        # Par défaut, retourner player1
        return "player1"
    
    def _get_model_for_player(self, player_id: Optional[str]) -> str:
        """Retourne le modèle configuré pour un joueur donné"""
        if not player_id:
            return self.game_settings.get("game", {}).get("default_model", "gpt-4.1-mini")
        
        # Chercher le modèle pour ce joueur
        player_settings = self.game_settings.get("players", {}).get(player_id, {})
        model = player_settings.get("model")
        
        # Si pas de modèle spécifique, utiliser le modèle par défaut
        if not model:
            model = self.game_settings.get("game", {}).get("default_model", "gpt-4.1-mini")
        
        print(f"🤖 Utilisation du modèle {model} pour {player_settings.get('name', player_id)}")
        return model
    
    def _get_player_name(self, player_id: Optional[str], game_context: Dict) -> str:
        """Retourne le nom du joueur depuis le contexte ou les settings"""
        if not player_id:
            return "Unknown"
        
        # Chercher dans le contexte du jeu
        players = game_context.get("players", {})
        if player_id in players:
            return players[player_id].get("name", player_id)
        
        # Chercher dans les settings
        player_settings = self.game_settings.get("players", {}).get(player_id, {})
        return player_settings.get("name", player_id)


if __name__ == "__main__":
    print("AI Service - Standalone Mode")
    print("=" * 50)
    print()
    
    # Create a simple event bus for standalone mode
    from flask import Flask
    app = Flask(__name__)
    event_bus = EventBus(app)
    
    # Initialize AI Service
    ai_service = AIService(event_bus)
    
    if ai_service.available:
        print("✅ AI Service is ready")
        print("   - OpenAI API key found")
        print("   - Waiting for decision requests...")
    else:
        print("❌ AI Service is NOT available")
        print("   - No OpenAI API key found")
        print("   - Set OPENAI_API_KEY environment variable")
    
    print()
    print("This service normally runs integrated with the main Flask app.")
    print("Running in standalone mode for testing only.")
    
    # Keep the service running
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nAI Service stopped.")