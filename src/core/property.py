from src.core.attributes import StringAttribute, IntAttribute, FixedArrayAttribute
from .memory_reader import MemoryReader
import json
import os

class Property:
    name = StringAttribute(0x8)
    position = IntAttribute(0x48)
    price = IntAttribute(0x64)
    rents = FixedArrayAttribute(0x74, 6)
    
    # Dictionnaire pour stocker les données statiques depuis MonopolyProperties.json
    _property_data = None

    def __init__(self, base):
        self._base = base
        self._load_property_data()
    
    @classmethod
    def _load_property_data(cls):
        """Charge les données des propriétés depuis MonopolyProperties.json"""
        if cls._property_data is None:
            try:
                json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'game_files', 'MonopolyProperties.json')
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._property_data = {prop['name']: prop for prop in data['properties']}
            except Exception as e:
                print(f"Erreur lors du chargement de MonopolyProperties.json: {e}")
                cls._property_data = {}
    
    @property
    def house_cost(self):
        """Retourne le coût d'une maison pour cette propriété"""
        if self._property_data and self.name in self._property_data:
            return self._property_data[self.name].get('houseCost', 0)
        return 0
    
    @property
    def mortgage_value(self):
        """Retourne la valeur hypothécaire de la propriété"""
        if self._property_data and self.name in self._property_data:
            return self._property_data[self.name].get('mortgage', 0)
        return self.price // 2  # Par défaut, la moitié du prix
    
    def get_set_price(self, house_count=3):
        """Calcule le prix d'un set de maisons (par défaut 3 maisons)"""
        return self.house_cost * house_count
    
    def get_house_sell_price(self, house_count=1):
        """Calcule le prix de revente d'une ou plusieurs maisons (moitié du prix d'achat)"""
        return (self.house_cost * house_count) // 2
    
    def get_set_sell_price(self, house_count=3):
        """Calcule le prix de revente d'un set de maisons"""
        return self.get_set_price(house_count) // 2
    
    def get_unmortgage_price(self):
        """Calcule le prix pour lever l'hypothèque (mortgage + 10%)"""
        return int(self.mortgage_value * 1.1)
    
    @property
    def is_mortgaged(self):
        """Vérifie si la propriété est hypothéquée en lisant l'adresse mémoire"""
        if self._property_data and self.name in self._property_data:
            mortgage_address = self._property_data[self.name].get('adresse_mortgage')
            if mortgage_address:
                try:
                    # Convertir l'adresse hexadécimale en entier
                    address = int(mortgage_address, 16)
                    # Lire le byte à cette adresse (0 = non hypothéquée, 1 = hypothéquée)
                    mortgage_status = MemoryReader.get_byte(address)
                    return mortgage_status == 1
                except Exception as e:
                    print(f"Erreur lors de la lecture du statut d'hypothèque pour {self.name}: {e}")
                    return False
        return False
    
    def get_property_info(self):
        """Retourne toutes les informations calculées de la propriété"""
        return {
            'name': self.name,
            'price': self.price,
            'house_cost': self.house_cost,
            'mortgage': self.mortgage_value,
            'is_mortgaged': self.is_mortgaged,
            'set_price_3_houses': self.get_set_price(3),
            'house_sell_price': self.get_house_sell_price(1),
            'set_sell_price_3_houses': self.get_set_sell_price(3),
            'unmortgage_price': self.get_unmortgage_price()
        }
    
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
    
    @staticmethod
    def is_property_mortgaged(property_name):
        """Vérifie si une propriété est hypothéquée par son nom"""
        # Charger les données des propriétés
        if Property._property_data is None:
            Property._load_property_data()
        
        if Property._property_data and property_name in Property._property_data:
            mortgage_address = Property._property_data[property_name].get('adresse_mortgage')
            if mortgage_address:
                try:
                    # Convertir l'adresse hexadécimale en entier
                    address = int(mortgage_address, 16)
                    # Lire le byte à cette adresse (0 = non hypothéquée, 1 = hypothéquée)
                    mortgage_status = MemoryReader.get_byte(address)
                    return mortgage_status == 1
                except Exception as e:
                    print(f"Erreur lors de la lecture du statut d'hypothèque pour {property_name}: {e}")
                    return False
        return False