#!/usr/bin/env python3
"""
Script pour vérifier que les clés API sont correctement configurées
"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

print("🔍 Vérification des clés API...\n")

# Vérifier chaque clé
keys_status = {
    "OPENAI_API_KEY": {
        "name": "OpenAI",
        "prefix": "sk-",
        "emoji": "🤖"
    },
    "ANTHROPIC_API_KEY": {
        "name": "Anthropic (Claude)",
        "prefix": "sk-ant-",
        "emoji": "🧠"
    },
    "GEMINI_API_KEY": {
        "name": "Google Gemini",
        "prefix": "AIza",
        "emoji": "💎"
    }
}

all_configured = True

for key_name, info in keys_status.items():
    api_key = os.getenv(key_name)
    
    if api_key and len(api_key) > 10:
        # Vérifier le préfixe si spécifié
        if api_key.startswith(info["prefix"]):
            print(f"{info['emoji']} {info['name']}: ✅ Configurée (commence par {info['prefix']}...)")
        else:
            print(f"{info['emoji']} {info['name']}: ⚠️  Configurée mais format inhabituel")
    else:
        print(f"{info['emoji']} {info['name']}: ❌ Non configurée")
        all_configured = False

print("\n" + "="*50)

if all_configured:
    print("✅ Toutes les clés API sont configurées!")
    print("Vous pouvez utiliser tous les providers AI.")
else:
    print("⚠️  Certaines clés API ne sont pas configurées.")
    print("Ajoutez-les dans le fichier .env pour utiliser tous les providers.")

print("\n💡 Pour obtenir des clés API:")
print("   - OpenAI: https://platform.openai.com/api-keys")
print("   - Anthropic: https://console.anthropic.com/settings/keys")
print("   - Google Gemini: https://makersuite.google.com/app/apikey")