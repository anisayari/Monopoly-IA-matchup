from src.core.property import Property
from src.core.memory_reader import MemoryReader
import json
import os

def get_all_properties_house_count():
    """Récupère le nombre de maisons pour toutes les propriétés"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'game_files', 'starting_state.jsonc')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            # Enlever les commentaires du JSONC
            content = f.read()
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                # Enlever les commentaires de type //
                comment_pos = line.find('//')
                if comment_pos != -1:
                    line = line[:comment_pos]
                cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines)
            data = json.loads(cleaned_content)
        
        # Récupérer toutes les adresses des propriétés
        house_addresses = data.get('house_number_by_property', [])
        
        property_houses = {}
        for prop in house_addresses:
            address = prop['address']
            label = prop['label']
            # Lire le nombre de maisons à cette adresse
            house_count = MemoryReader.get_byte(address)
            property_houses[label] = house_count
        
        return property_houses
        
    except Exception as e:
        print(f"Erreur lors de la lecture des nombres de maisons: {e}")
        return {}

def get_property_house_count(property_name):
    """Récupère le nombre de maisons pour une propriété spécifique
    
    Args:
        property_name: Le nom de la propriété (ex: "Old Kent Road")
    
    Returns:
        Le nombre de maisons (0-5, où 5 = hôtel) ou None si non trouvé
    """
    return Property.get_house_count_for_property(property_name)

def has_hotel(property_name):
    """Vérifie si une propriété a un hôtel
    
    Args:
        property_name: Le nom de la propriété
    
    Returns:
        True si la propriété a un hôtel (5 maisons), False sinon
    """
    house_count = get_property_house_count(property_name)
    return house_count == 5 if house_count is not None else False

def can_build_house(property_name):
    """Vérifie si on peut construire une maison sur cette propriété
    
    Args:
        property_name: Le nom de la propriété
    
    Returns:
        True si on peut construire (moins de 4 maisons), False sinon
    """
    house_count = get_property_house_count(property_name)
    return house_count is not None and house_count < 4

def can_build_hotel(property_name):
    """Vérifie si on peut construire un hôtel sur cette propriété
    
    Args:
        property_name: Le nom de la propriété
    
    Returns:
        True si on peut construire un hôtel (exactement 4 maisons), False sinon
    """
    house_count = get_property_house_count(property_name)
    return house_count == 4