#!/usr/bin/env python3
"""
Test direct du service AI pour vérifier qu'il envoie bien les messages
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import get_ai_service
import json

# Créer un contexte de jeu de test
game_context = {
    "global": {
        "current_player": "player1",
        "current_turn": 5
    },
    "players": {
        "player1": {
            "name": "GPT1",
            "money": 1500,
            "current_space": "Park Lane",
            "properties": []
        },
        "player2": {
            "name": "Claude",
            "money": 1200,
            "current_space": "Mayfair",
            "properties": []
        }
    }
}

# Initialiser le service AI
print("Initialisation du service AI...")
ai_service = get_ai_service()

# Tester une décision
print("\nTest d'une décision d'achat...")
result = ai_service.make_decision(
    popup_text="Do you want to buy Park Lane for £350?",
    options=["Buy", "Auction", "Cancel"],
    game_context=game_context
)

print(f"\nRésultat de la décision:")
print(f"  Decision: {result['decision']}")
print(f"  Reason: {result['reason']}")
print(f"  Confidence: {result['confidence']}")

print("\n✅ Test terminé! Vérifiez:")
print("   1. Les logs [AI Chat] dans cette console")
print("   2. La fenêtre du serveur AI Chat (si lancé)")