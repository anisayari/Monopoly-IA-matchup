#!/usr/bin/env python3
"""
Script de test pour récupérer le nombre de maisons sur les propriétés
"""

import dolphin_memory_engine as dme
from src.utils.property_helpers import (
    get_property_house_count, 
    get_all_properties_house_count,
    has_hotel,
    can_build_house,
    can_build_hotel
)
from src.core.property import Property

def test_house_count():
    print("=== Test de récupération du nombre de maisons ===\n")
    
    # Se connecter à Dolphin
    try:
        dme.hook()
    except:
        pass
    
    if not dme.is_hooked():
        print("❌ Dolphin n'est pas connecté. Assurez-vous que Dolphin est lancé avec Monopoly.")
        return
    
    print("✅ Connecté à Dolphin\n")
    
    # Test pour une propriété spécifique
    property_name = "Park Lane"
    house_count = get_property_house_count(property_name)
    
    if house_count is not None:
        print(f"Propriété: {property_name}")
        print(f"Nombre de maisons: {house_count}")
        if house_count == 5:
            print("→ Cette propriété a un hôtel!")
        elif house_count > 0:
            print(f"→ Cette propriété a {house_count} maison(s)")
        else:
            print("→ Aucune construction sur cette propriété")
        
        print(f"A un hôtel? {has_hotel(property_name)}")
        print(f"Peut construire une maison? {can_build_house(property_name)}")
        print(f"Peut construire un hôtel? {can_build_hotel(property_name)}")
    else:
        print(f"❌ Impossible de lire le nombre de maisons pour {property_name}")
    
    print("\n" + "="*50 + "\n")
    
    # Test pour toutes les propriétés
    print("=== Nombre de maisons sur toutes les propriétés ===\n")
    all_properties = get_all_properties_house_count()
    
    if all_properties:
        for prop_name, count in all_properties.items():
            status = ""
            if count == 5:
                status = " 🏨 (Hôtel)"
            elif count > 0:
                status = f" 🏠 x{count}"
            
            print(f"{prop_name:<30} : {count}{status}")
    else:
        print("❌ Impossible de récupérer les informations des propriétés")
    
    print("\n" + "="*50 + "\n")
    
    # Test avec la méthode statique directement
    print("=== Test direct avec Property.get_house_count_for_property ===\n")
    test_properties = ["Old Kent Road", "Mayfair", "Oxford Street"]
    
    for prop in test_properties:
        count = Property.get_house_count_for_property(prop)
        if count is not None:
            print(f"{prop}: {count} maison(s)")
        else:
            print(f"{prop}: Erreur de lecture")

if __name__ == "__main__":
    test_house_count()