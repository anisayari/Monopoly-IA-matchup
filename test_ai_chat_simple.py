#!/usr/bin/env python3
"""
Test simple pour vérifier que le serveur AI Chat fonctionne
"""

import requests
import json
from datetime import datetime

# Test de base
try:
    # Test de santé
    response = requests.get("http://localhost:8003/health")
    print(f"✅ Health check: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    # Test d'envoi de pensée
    thought_data = {
        'player': 'GPT1',
        'type': 'analysis',
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
    
    response = requests.post("http://localhost:8003/thought", json=thought_data)
    print(f"\n✅ Thought sent: {response.status_code}")
    
    # Test d'envoi de chat
    chat_data = {
        'from': 'GPT1',
        'to': 'All',
        'message': 'Test message from GPT1!',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    response = requests.post("http://localhost:8003/chat", json=chat_data)
    print(f"✅ Chat sent: {response.status_code}")
    
    print("\n✨ Tests réussis! Vérifiez la fenêtre du serveur AI Chat.")
    
except requests.exceptions.ConnectionError:
    print("❌ Erreur: Le serveur AI Chat n'est pas accessible sur le port 8003")
    print("   Assurez-vous que START_AI_CHAT.bat est lancé")
except Exception as e:
    print(f"❌ Erreur: {e}")