#!/usr/bin/env python3
"""
Test simple et direct pour lire le nombre de maisons
"""

import dolphin_memory_engine as dme
from src.core.memory_reader import MemoryReader

def main():
    print("Test simple de lecture des maisons\n")
    
    # Connexion à Dolphin
    print("1. Connexion à Dolphin...")
    try:
        dme.hook()
        print("   ✅ dme.hook() exécuté")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    print(f"   État de connexion: {dme.is_hooked()}\n")
    
    if not dme.is_hooked():
        print("❌ Pas de connexion. Vérifiez que Dolphin est lancé avec Monopoly.")
        return
    
    # Test de lecture directe
    print("2. Test de lecture directe des adresses de maisons:\n")
    
    # Quelques propriétés avec leurs adresses
    properties = [
        ("Old Kent Road", 0x9303E327),
        ("Whitechapel Road", 0x9303E3CF),
        ("Park Lane", 0x9303F437),
        ("Mayfair", 0x9303F4DF)
    ]
    
    for prop_name, address in properties:
        try:
            # Lire 1 byte à l'adresse
            value = MemoryReader.get_byte(address)
            print(f"{prop_name} (0x{address:08X}): {value} maison(s)")
            
            # Affichage visuel
            if value == 0:
                print("   → Aucune construction")
            elif value <= 4:
                print(f"   → {'🏠' * value}")
            elif value == 5:
                print("   → 🏨 (Hôtel)")
            else:
                print(f"   → ⚠️  Valeur inhabituelle: {value}")
            print()
            
        except Exception as e:
            print(f"{prop_name}: ❌ Erreur de lecture - {e}\n")
    
    # Test avec la fonction helper
    print("\n3. Test avec la fonction get_property_house_count:\n")
    
    from src.utils.property_helpers import get_property_house_count
    
    for prop_name, _ in properties:
        try:
            count = get_property_house_count(prop_name)
            if count is not None:
                print(f"{prop_name}: {count} maison(s)")
            else:
                print(f"{prop_name}: ❌ Retour None")
        except Exception as e:
            print(f"{prop_name}: ❌ Exception - {e}")

if __name__ == "__main__":
    main()