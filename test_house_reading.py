#!/usr/bin/env python3
"""
Test complet pour vérifier la lecture du nombre de maisons sur les propriétés
"""

import dolphin_memory_engine as dme
import time
import sys
from src.utils.property_helpers import (
    get_property_house_count, 
    get_all_properties_house_count,
    has_hotel,
    can_build_house,
    can_build_hotel
)
from src.core.property import Property

def wait_for_dolphin():
    """Attend que Dolphin soit connecté"""
    print("⏳ En attente de connexion à Dolphin...")
    
    # Essayer de se connecter directement
    try:
        dme.hook()
    except Exception as e:
        print(f"   Erreur lors de la connexion: {e}")
    
    # Vérifier si connecté
    if dme.is_hooked():
        print("✅ Connecté à Dolphin!")
        return True
    
    # Si pas connecté, essayer plusieurs fois
    attempts = 0
    while attempts < 10:
        try:
            dme.hook()
            time.sleep(0.5)  # Attendre un peu
            if dme.is_hooked():
                print("✅ Connecté à Dolphin!")
                return True
        except:
            pass
        attempts += 1
        print(f"   Tentative {attempts}/10...")
        time.sleep(1)
    
    return False

def test_single_property():
    """Test de lecture pour une propriété spécifique"""
    print("\n" + "="*60)
    print("TEST 1: Lecture d'une propriété spécifique")
    print("="*60 + "\n")
    
    test_properties = [
        "Old Kent Road",
        "Whitechapel Road", 
        "Park Lane",
        "Mayfair",
        "Oxford Street",
        "Bond Street"
    ]
    
    for property_name in test_properties:
        print(f"\n🏠 Test pour: {property_name}")
        print("-" * 40)
        
        # Récupérer le nombre de maisons
        house_count = get_property_house_count(property_name)
        
        if house_count is not None:
            print(f"✅ Nombre de maisons/hôtel: {house_count}")
            
            # Afficher l'état
            if house_count == 0:
                print("   → Aucune construction")
            elif house_count == 1:
                print("   → 1 maison 🏠")
            elif house_count <= 4:
                print(f"   → {house_count} maisons 🏠" * house_count)
            elif house_count == 5:
                print("   → 1 hôtel 🏨")
            
            # Tester les fonctions helper
            print(f"   → A un hôtel? {has_hotel(property_name)}")
            print(f"   → Peut construire une maison? {can_build_house(property_name)}")
            print(f"   → Peut construire un hôtel? {can_build_hotel(property_name)}")
        else:
            print("❌ Erreur: Impossible de lire cette propriété")

def test_all_properties():
    """Test de lecture pour toutes les propriétés"""
    print("\n" + "="*60)
    print("TEST 2: Lecture de toutes les propriétés")
    print("="*60 + "\n")
    
    all_properties = get_all_properties_house_count()
    
    if not all_properties:
        print("❌ Erreur: Impossible de récupérer les propriétés")
        return
    
    # Grouper par couleur (approximatif basé sur l'ordre)
    color_groups = {
        "Marron": ["Old Kent Road", "Whitechapel Road"],
        "Bleu clair": ["The Angel Islington", "Euston Road", "Pentonville Road"],
        "Rose": ["Pall Mall", "Whitehall", "Northumberland Avenue"],
        "Orange": ["Bow Street", "Marlborough Street", "Vine Street"],
        "Rouge": ["Strand", "Fleet Street", "Trafalgar Square"],
        "Jaune": ["Leicester Square", "Coventry Street", "Piccadilly"],
        "Vert": ["Regent Street", "Oxford Street", "Bond Street"],
        "Bleu foncé": ["Park Lane", "Mayfair"]
    }
    
    total_houses = 0
    total_hotels = 0
    
    for color, properties in color_groups.items():
        print(f"\n{color}:")
        print("-" * 40)
        
        for prop in properties:
            if prop in all_properties:
                count = all_properties[prop]
                
                # Symboles visuels
                if count == 0:
                    visual = "⬜"
                elif count <= 4:
                    visual = "🏠" * count
                    total_houses += count
                else:  # count == 5
                    visual = "🏨"
                    total_hotels += 1
                
                print(f"  {prop:<30} [{count}] {visual}")
    
    print("\n" + "="*60)
    print("RÉSUMÉ:")
    print(f"  Total maisons: {total_houses} 🏠")
    print(f"  Total hôtels: {total_hotels} 🏨")
    print(f"  Valeur totale en constructions: {total_houses + total_hotels * 5}")

def test_memory_direct():
    """Test direct de lecture mémoire"""
    print("\n" + "="*60)
    print("TEST 3: Lecture directe de la mémoire")
    print("="*60 + "\n")
    
    # Test avec quelques adresses directement
    test_addresses = [
        ("Old Kent Road", "0x9303E327"),
        ("Park Lane", "0x9303F437"),
        ("Mayfair", "0x9303F4DF")
    ]
    
    for prop_name, address in test_addresses:
        try:
            # Utiliser directement Property.get_house_count_for_property
            count_method = Property.get_house_count_for_property(prop_name)
            
            # Lire directement l'adresse
            from src.core.memory_reader import MemoryReader
            count_direct = MemoryReader.get_byte(address)
            
            print(f"{prop_name}:")
            print(f"  → Via méthode: {count_method}")
            print(f"  → Lecture directe: {count_direct}")
            print(f"  → Match: {'✅' if count_method == count_direct else '❌'}")
            
        except Exception as e:
            print(f"❌ Erreur pour {prop_name}: {e}")

def main():
    """Fonction principale"""
    print("\n🎲 TEST DE LECTURE DES MAISONS/HÔTELS MONOPOLY 🎲")
    print("="*60)
    
    # Se connecter à Dolphin
    if not wait_for_dolphin():
        print("\n❌ Impossible de se connecter à Dolphin!")
        print("Assurez-vous que:")
        print("  1. Dolphin est lancé")
        print("  2. Monopoly est en cours d'exécution")
        print("  3. Une partie est chargée")
        sys.exit(1)
    
    print("\n✅ Connexion établie! Début des tests...\n")
    time.sleep(1)
    
    try:
        # Exécuter les tests
        test_single_property()
        input("\n📝 Appuyez sur Entrée pour continuer avec le test suivant...")
        
        test_all_properties()
        input("\n📝 Appuyez sur Entrée pour continuer avec le test suivant...")
        
        test_memory_direct()
        
        print("\n" + "="*60)
        print("✅ TOUS LES TESTS TERMINÉS!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur pendant les tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()