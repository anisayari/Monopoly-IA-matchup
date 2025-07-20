from src.core.attributes import StringAttribute, IntAttribute, FixedArrayAttribute
from .memory_reader import MemoryReader
import json
import os

class Property:
    name = StringAttribute(0x8)
    position = IntAttribute(0x48)
    price = IntAttribute(0x64)
    rents = FixedArrayAttribute(0x74, 6)

    def __init__(self, base):
        self._base = base
    
    @staticmethod
    def get_house_count_for_property(property_name):
        """Récupère le nombre de maisons sur une propriété donnée"""
        # Charger les adresses depuis le fichier de configuration
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
            
            # Trouver l'adresse correspondant à la propriété
            house_addresses = data.get('house_number_by_property', [])
            
            for prop in house_addresses:
                if prop['label'].lower() == property_name.lower():
                    address = prop['address']
                    # Lire le nombre de maisons à cette adresse
                    house_count = MemoryReader.get_byte(address)
                    return house_count
            
            # Si la propriété n'est pas trouvée
            return None
            
        except Exception as e:
            print(f"Erreur lors de la lecture du nombre de maisons: {e}")
            return None