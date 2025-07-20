#!/usr/bin/env python3
"""
Script pour corriger l'historique AI si des objets JSON ont été sauvegardés au lieu de strings
"""

import json
import os

def fix_ai_history():
    history_file = os.path.join('contexte', 'ai_history.json')
    
    if not os.path.exists(history_file):
        print("❌ Fichier d'historique non trouvé")
        return
    
    print("📂 Lecture de l'historique...")
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    fixed = False
    
    # Vérifier et corriger player1_history
    if 'player1' in history:
        print(f"\nVérification de player1 ({len(history['player1'])} messages)...")
        for i, msg in enumerate(history['player1']):
            if 'content' in msg and isinstance(msg['content'], dict):
                print(f"  ⚠️  Message {i} contient un objet au lieu d'une string")
                print(f"     Avant: {type(msg['content'])}")
                # Convertir l'objet en string JSON
                msg['content'] = json.dumps(msg['content'])
                print(f"     Après: {type(msg['content'])}")
                fixed = True
    
    # Vérifier et corriger player2_history
    if 'player2' in history:
        print(f"\nVérification de player2 ({len(history['player2'])} messages)...")
        for i, msg in enumerate(history['player2']):
            if 'content' in msg and isinstance(msg['content'], dict):
                print(f"  ⚠️  Message {i} contient un objet au lieu d'une string")
                print(f"     Avant: {type(msg['content'])}")
                # Convertir l'objet en string JSON
                msg['content'] = json.dumps(msg['content'])
                print(f"     Après: {type(msg['content'])}")
                fixed = True
    
    if fixed:
        # Sauvegarder une copie de sauvegarde
        backup_file = history_file + '.backup'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Sauvegarde créée: {backup_file}")
        
        # Sauvegarder l'historique corrigé
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"✅ Historique corrigé et sauvegardé!")
    else:
        print("\n✅ Aucun problème détecté dans l'historique")
    
    # Afficher un échantillon de l'historique
    print("\n📋 Échantillon de l'historique:")
    for player in ['player1', 'player2']:
        if player in history and history[player]:
            print(f"\n{player} - Dernier message:")
            last_msg = history[player][-1]
            content = last_msg['content']
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"  Role: {last_msg['role']}")
            print(f"  Content type: {type(last_msg['content'])}")
            print(f"  Content: {content}")

if __name__ == "__main__":
    fix_ai_history()