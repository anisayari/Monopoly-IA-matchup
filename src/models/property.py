from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Property:
    """Représente une propriété du jeu Monopoly"""
    id: str
    name: str
    price: int
    mortgage: int
    rents: List[int]
    house_cost: int

    @staticmethod
    def safe_int(value: str, default: int = 0) -> int:
        """Convertit une chaîne en entier de manière sécurisée"""
        try:
            return int(value) if value.strip() else default
        except (ValueError, AttributeError):
            return default

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Property':
        """Crée une instance de Property à partir d'un dictionnaire"""
        return cls(
            id=data.get('hybridname', ''),
            name=data.get('property', ''),
            price=cls.safe_int(data.get('value', '0')),
            mortgage=cls.safe_int(data.get('mortgage', '0')),
            rents=[
                cls.safe_int(data.get('rent0', '0')),
                cls.safe_int(data.get('rent1', '0')),
                cls.safe_int(data.get('rent2', '0')),
                cls.safe_int(data.get('rent3', '0')),
                cls.safe_int(data.get('rent4', '0')),
                cls.safe_int(data.get('rent5', '0'))
            ],
            house_cost=cls.safe_int(data.get('housecost', '0'))
        ) 