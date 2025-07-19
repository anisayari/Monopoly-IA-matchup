#!/usr/bin/env python3
"""
Script de test pour vérifier la lecture/écriture des noms de joueurs
"""

import dolphin_memory_engine as dme
from src.core.game_loader import GameLoader
from src.game.monopoly import MonopolyGame

def test_player_names():
    print("🔧 Test de lecture/écriture des noms de joueurs")
    
    try:
        # Se connecter à Dolphin
        dme.hook()
        if not dme.is_hooked():
            print("❌ Impossible de se connecter à Dolphin Memory Engine")
            print("   Assurez-vous que Dolphin est lancé avec le jeu Monopoly")
            return
        
        print("✅ Connecté à Dolphin Memory Engine")
        
        # Charger les données du jeu
        data = GameLoader("game_files/starting_state.jsonc", "game_files/starting_state.sav")
        game = MonopolyGame(data)
        
        print(f"\n📊 Nombre de joueurs détectés: {len(game.players)}")
        
        for i, player in enumerate(game.players):
            print(f"\n🎮 Joueur {i+1} (ID: {player.id}):")
            
            # Lire le nom actuel
            current_name = player.name
            print(f"   Nom actuel: '{current_name}'")
            
            # Essayer d'écrire un nouveau nom
            new_name = f"GPT{i+1}"
            print(f"   Écriture du nouveau nom: '{new_name}'")
            player.name = new_name
            
            # Relire pour vérifier
            verified_name = player.name
            print(f"   Nom après écriture: '{verified_name}'")
            
            if verified_name == new_name:
                print(f"   ✅ Écriture réussie!")
            else:
                print(f"   ❌ Échec de l'écriture (nom lu: '{verified_name}')")
            
            # Afficher aussi l'argent
            print(f"   💰 Argent: ${player.money}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_player_names()