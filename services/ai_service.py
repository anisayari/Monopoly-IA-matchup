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
            
            # Préparer le contexte
            context_str = self._format_game_context(game_context)
            
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
                    }
                },
                "required": ["choice", "reason"],
                "additionalProperties": False
            }

            # Construire le message utilisateur
            user_message = (
                f"Tu es un expert du Monopoly.\n"
                f"Contexte actuel:\n{context_str}\n\n"
                f"Popup: \"{popup_text}\"\n"
                f"Options disponibles: {', '.join(option_names)}\n\n"
            )

            # Appeler l'API avec Structured Outputs
            response = self.client.responses.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Expert Monopoly. Réponds uniquement avec un JSON valide conforme au schéma."},
                    {"role": "user", "content": user_message}
                ],
                response_format={
                    "type": "json_schema",
                    "schema": schema,
                    "strict": True
                },
                temperature=0.1,
                max_tokens=100
            )

            # Extraire la réponse JSON
            result_json_str = getattr(response, "output_text", None)

            data = json.loads(result_json_str)

            choice = str(data.get("choice", "")).lower()
            reason = data.get("reason", "Décision stratégique")
            confidence = float(data.get("confidence", 0.9))

            # Vérifier que le choix est valide
            if choice not in option_names:
                print(f"⚠️  IA a choisi '{choice}' qui n'est pas dans les options")
                return self._default_decision(options)
            
            return {
                'choice': choice,
                'reason': reason,
                'confidence': confidence
            }
            
        except Exception as e:
            print(f"⚠️  Erreur IA: {e}")
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