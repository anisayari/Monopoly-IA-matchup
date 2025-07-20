#!/usr/bin/env python3
"""
Test pour vérifier que le contexte récupère bien les informations des maisons
"""

import json
import os
import dolphin_memory_engine as dme
from src.game.monopoly import MonopolyGame
from src.game.listeners import MonopolyListeners
from src.game.contexte import Contexte

def test_context_with_houses():
    print("=== Test du contexte avec les maisons/hôtels ===\n")
    
    # Se connecter à Dolphin
    try:
        dme.hook()
    except:
        pass
    
    if not dme.is_hooked():
        print("❌ Dolphin n'est pas connecté. Assurez-vous que Dolphin est lancé avec Monopoly.")
        return
    
    print("✅ Connecté à Dolphin\n")
    
    try:
        # Initialiser le jeu et le contexte
        print("Initialisation du jeu et du contexte...")
        game = MonopolyGame()
        listeners = MonopolyListeners(game)
        contexte = Contexte(game, listeners)
        
        print("✅ Contexte initialisé\n")
        
        # Forcer une mise à jour du contexte
        contexte._update_context()
        contexte._save_context()
        
        # Lire le fichier de contexte
        context_file = os.path.join("contexte", "game_context.json")
        if os.path.exists(context_file):
            with open(context_file, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            
            print("📋 Propriétés avec des constructions:\n")
            
            # Afficher les propriétés avec des maisons/hôtels
            properties = context_data.get("global", {}).get("properties", [])
            properties_with_buildings = [p for p in properties if p.get("houses", 0) > 0]
            
            if properties_with_buildings:
                for prop in properties_with_buildings:
                    name = prop["name"]
                    houses = prop["houses"]
                    owner = prop.get("owner", "Aucun")
                    current_rent = prop.get("current_rent", 0)
                    
                    if houses == 5:
                        print(f"🏨 {name}: 1 hôtel")
                    else:
                        print(f"🏠 {name}: {houses} maison(s)")
                    
                    print(f"   Propriétaire: {owner}")
                    print(f"   Loyer actuel: {current_rent}€")
                    print()
            else:
                print("Aucune propriété avec des constructions pour le moment.\n")
            
            # Afficher le résumé des constructions
            buildings_summary = context_data.get("global", {}).get("buildings_summary", {})
            if buildings_summary:
                print("\n📊 Résumé des constructions:")
                print(f"   Total maisons: {buildings_summary.get('total_houses', 0)}")
                print(f"   Total hôtels: {buildings_summary.get('total_hotels', 0)}")
                
                houses_list = buildings_summary.get('properties_with_houses', [])
                if houses_list:
                    print("\n   Propriétés avec maisons:")
                    for prop in houses_list:
                        print(f"   - {prop['name']}: {prop['houses']} maison(s) (Propriétaire: {prop['owner']})")
                
                hotels_list = buildings_summary.get('properties_with_hotels', [])
                if hotels_list:
                    print("\n   Propriétés avec hôtels:")
                    for prop in hotels_list:
                        print(f"   - {prop['name']} (Propriétaire: {prop['owner']})")
            
            # Afficher un exemple de propriété complète
            print("\n\n📄 Exemple de données complètes d'une propriété:")
            if properties:
                example_prop = properties[0]
                print(json.dumps(example_prop, indent=2, ensure_ascii=False))
            
        else:
            print("❌ Fichier de contexte non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_context_with_houses()