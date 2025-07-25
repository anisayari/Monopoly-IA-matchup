"""
Utilitaires pour la gestion des propriétés Monopoly
"""

import json
import os
from typing import Dict, Tuple, Optional, Union


class PropertyManager:
    """Gestionnaire pour les propriétés Monopoly avec leurs coordonnées et détails"""
    
    def __init__(self):
        self.properties = {}
        self.properties_by_name = {}
        self.load_properties()
    
    def load_properties(self):
        """Charge les propriétés depuis MonopolyProperties.json"""
        try:
            properties_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "game_files", 
                "MonopolyProperties.json"
            )
            
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Indexer par ID et par nom
                for prop in data.get('properties', []):
                    self.properties[prop['id']] = prop
                    self.properties_by_name[prop['name'].lower()] = prop
                    
                print(f"✅ PropertyManager: Loaded {len(self.properties)} properties")
            else:
                print(f"⚠️ PropertyManager: MonopolyProperties.json not found at {properties_file}")
                
        except Exception as e:
            print(f"❌ PropertyManager: Error loading properties: {e}")
    
    def get_coordinates(self, property_name: str, coord_type: str = 'relative') -> Optional[Tuple[float, float]]:
        """
        Récupère les coordonnées d'une propriété
        
        Args:
            property_name: Nom de la propriété
            coord_type: 'relative' (0.0-1.0) ou 'absolute' (pixels)
            
        Returns:
            Tuple (x, y) ou None si propriété non trouvée
        """
        prop = self.properties_by_name.get(property_name.lower())
        if not prop:
            # Essayer de trouver par ID
            prop = self.properties.get(property_name)
            
        if prop and 'coordinates' in prop:
            coords = prop['coordinates']
            if coord_type == 'relative':
                return (coords['x_relative'], coords['y_relative'])
            elif coord_type == 'absolute':
                return (coords['x_pixel'], coords['y_pixel'])
                
        return None
    
    def get_property_details(self, property_name: Union[str, int]) -> Optional[Dict]:
        """
        Récupère les détails d'une propriété
        
        Args:
            property_name: Nom de la propriété ou ID/position
            
        Returns:
            Dict avec value, mortgage, rent, type, etc. ou None
        """
        # Convertir en string si c'est un nombre
        property_name = str(property_name)
        
        # Chercher par nom d'abord
        prop = self.properties_by_name.get(property_name.lower())
        if not prop:
            # Essayer de trouver par ID
            prop = self.properties.get(property_name)
            
        if prop:
            details = {
                'id': prop.get('id'),
                'name': prop.get('name'),
                'value': prop.get('value'),
                'mortgage': prop.get('mortgage'),
                'type': prop.get('type'),
                'rent': prop.get('rent', {})
            }
            
            # Ajouter des infos spécifiques selon le type
            if prop['type'] == 'property':
                details['house_cost'] = prop.get('houseCost', 0)
                details['color_group'] = self._get_color_group(prop['value'])
            elif prop['type'] == 'station':
                details['station_count'] = 4  # Il y a 4 gares au total
            elif prop['type'] == 'utility':
                details['utility_count'] = 2  # Il y a 2 services publics
                
            return details
            
        return None
    
    def _get_color_group(self, value: int) -> str:
        """Détermine le groupe de couleur basé sur la valeur de la propriété"""
        if value <= 60:
            return "brown"
        elif value <= 120:
            return "light_blue"
        elif value <= 140:
            return "pink"
        elif value <= 180:
            return "orange"
        elif value <= 220:
            return "red"
        elif value <= 260:
            return "yellow"
        elif value <= 300:
            return "green"
        else:
            return "dark_blue"
    
    def get_all_properties(self) -> Dict:
        """Retourne toutes les propriétés"""
        return self.properties
    
    def get_property_by_position(self, position: int) -> Optional[Dict]:
        """
        Trouve une propriété par sa position sur le plateau (0-39)
        
        Args:
            position: Position sur le plateau (0-39)
            
        Returns:
            Dict de la propriété ou None
        """
        # Les positions correspondent généralement aux IDs dans un ordre spécifique
        # Mais il faut mapper correctement
        position_map = {
            1: "Property00",   # Old Kent Road
            3: "Property01",   # Whitechapel Road
            5: "Property02",   # Kings Cross Station
            6: "Property03",   # The Angel Islington
            8: "Property04",   # Euston Road
            9: "Property05",   # Pentonville Road
            11: "Property06",  # Pall Mall
            12: "Property07",  # Electric Company
            13: "Property08",  # Whitehall
            14: "Property09",  # Northumberland Avenue
            15: "Property10",  # Marylebone Station
            16: "Property11",  # Bow Street
            18: "Property12",  # Marlborough Street
            19: "Property13",  # Vine Street
            21: "Property14",  # Strand
            23: "Property15",  # Fleet Street
            24: "Property16",  # Trafalgar Square
            25: "Property17",  # Fenchurch St. Station
            26: "Property18",  # Leicester Square
            27: "Property19",  # Water Works
            28: "Property20",  # Coventry Street
            29: "Property21",  # Piccadilly
            31: "Property22",  # Regent Street
            32: "Property23",  # Oxford Street
            34: "Property24",  # Bond Street
            35: "Property25",  # Liverpool St. Station
            37: "Property26",  # Park Lane
            39: "Property27",  # Mayfair
        }
        
        prop_id = position_map.get(position)
        if prop_id:
            return self.properties.get(prop_id)
        return None


# Instance globale
property_manager = PropertyManager()


# Fonctions utilitaires simples
def get_coordinates(property_name: str, coord_type: str = 'relative') -> Optional[Tuple[float, float]]:
    """
    Récupère les coordonnées d'une propriété
    
    Args:
        property_name: Nom de la propriété
        coord_type: 'relative' ou 'absolute'
        
    Returns:
        Tuple (x, y) ou None
    """
    return property_manager.get_coordinates(property_name, coord_type)


def get_property_details(property_name: str) -> Optional[Dict]:
    """
    Récupère les détails d'une propriété
    
    Args:
        property_name: Nom de la propriété
        
    Returns:
        Dict avec value, mortgage, rent, etc. ou None
    """
    return property_manager.get_property_details(property_name)