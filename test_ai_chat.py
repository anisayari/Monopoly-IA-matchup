#!/usr/bin/env python3
"""
Script de test pour vérifier que le chat AI fonctionne
"""

import requests
import json
from datetime import datetime

# URL du serveur de chat
CHAT_SERVER_URL = "http://localhost:8003"

def test_thought(player_name="GPT1", thought_type="analysis"):
    """Envoie une pensée de test au serveur"""
    data = {
        'player': player_name,
        'type': thought_type,
        'content': {
            'popup': 'Do you want to buy Park Lane for £350?',
            'options_count': 3,
            'argent': 1500
        },
        'context': {
            'tour': 5,
            'position': 'Park Lane'
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.post(f"{CHAT_SERVER_URL}/thought", json=data)
        print(f"✅ Pensée envoyée pour {player_name}: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur envoi pensée: {e}")

def test_decision(player_name="Claude", decision="Buy"):
    """Envoie une décision de test au serveur"""
    data = {
        'player': player_name,
        'type': 'decision',
        'content': {
            'choix': decision,
            'raison': 'Park Lane est une propriété stratégique pour compléter le monopole bleu foncé.',
            'confiance': '90%'
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.post(f"{CHAT_SERVER_URL}/thought", json=data)
        print(f"✅ Décision envoyée pour {player_name}: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur envoi décision: {e}")

def test_chat(from_player="GPT1", to_player="Claude", message="Belle acquisition avec Park Lane!"):
    """Envoie un message de chat de test"""
    data = {
        'from': from_player,
        'to': to_player,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    try:
        response = requests.post(f"{CHAT_SERVER_URL}/chat", json=data)
        print(f"✅ Chat envoyé de {from_player} à {to_player}: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur envoi chat: {e}")

def main():
    print("🧪 Test du serveur AI Chat...\n")
    
    # Test de santé
    try:
        response = requests.get(f"{CHAT_SERVER_URL}/health")
        if response.status_code == 200:
            print("✅ Serveur AI Chat actif!")
        else:
            print("❌ Serveur AI Chat ne répond pas correctement")
            return
    except:
        print("❌ Serveur AI Chat non accessible sur le port 8003")
        print("   Assurez-vous que ai_chat_server.py est lancé")
        return
    
    print("\n📤 Envoi de messages de test...\n")
    
    # Scénario 1: GPT1 analyse une situation
    test_thought("GPT1", "analysis")
    
    # Scénario 2: GPT1 prend une décision
    test_decision("GPT1", "Buy")
    
    # Scénario 3: GPT1 envoie un message de chat
    test_chat("GPT1", "All", "Je viens d'acheter Park Lane! 🏠")
    
    # Scénario 4: Claude répond
    test_thought("Claude", "analysis")
    test_decision("Claude", "Next Turn")
    test_chat("Claude", "GPT1", "Bien joué! Je garde mon argent pour le moment.")
    
    # Scénario 5: Conversation entre les IA
    test_chat("GPT1", "Claude", "Tu devrais acheter des propriétés orange, elles sont rentables!")
    test_chat("Claude", "GPT1", "Merci du conseil, mais je vise le monopole rouge 😉")
    
    print("\n✨ Tests terminés! Vérifiez la fenêtre du serveur AI Chat.")

if __name__ == "__main__":
    main()