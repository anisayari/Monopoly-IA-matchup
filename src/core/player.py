from src.core.attributes import DynamicArrayAttribute, IntAttribute
from src.core.property import Property
from .game_loader import PlayerData
from .memory_reader import MemoryReader

class Player:
    _data: PlayerData

    dice1 = IntAttribute(0x0)
    dice2 = IntAttribute(0x4)
    roll = IntAttribute(0x10)
    # L'offset 0x14C est le bon pour cette version du jeu
    properties = DynamicArrayAttribute(0x14C, Property)
    
    @property
    def owned_properties(self):
        """Retourne uniquement les propriétés réellement possédées (adresse != 0x0)"""
        all_props = self.properties
        valid_props = []
        seen_positions = set()  # Pour éviter les doublons
        
        for prop in all_props:
            try:
                # Vérifier si l'adresse de base est valide (pas 0x0 ou autres valeurs invalides)
                if prop._base > 0x10000 and prop._base < 0xFFFFFF00:
                    # Vérifier aussi que la position est valide (entre 0 et 39)
                    pos = prop.position
                    if 0 <= pos <= 39 and pos not in seen_positions:
                        valid_props.append(prop)
                        seen_positions.add(pos)
            except:
                pass
                
        return valid_props
    
    def __init__(self, data: PlayerData):
        self._data = data

    @property
    def _base(self) -> int:
        return MemoryReader.hex_to_int(self._data['address']['base'])
        
    @property
    def id(self):
        return self._data["id"]    
    
    @property
    def dices(self):
        return [self.dice1, self.dice2]

    @property
    def name(self):
        # Try different encodings to find the correct one
        name_addr = self._data["address"]["name"][0]
        # print(f"[DEBUG Player] Reading name for {self.id} from address {name_addr}")
        
        # Try little endian first (common for x86 systems)
        name = MemoryReader.get_string(name_addr, max_length=10, byteorder="little")
        
        # If name looks corrupted, try big endian
        if not name or any(ord(c) > 127 for c in name):
            # Ne logger que si vraiment nécessaire
            # print(f"[DEBUG Player] Name with little endian looks corrupted: '{name}', trying big endian")
            name = MemoryReader.get_string(name_addr, max_length=10, byteorder="big")
        
        # print(f"[DEBUG Player] Final name for {self.id}: '{name}'")
        return name
    
    @name.setter
    def name(self, value):
        # print(f"[DEBUG Player] Setting name for {self.id} to '{value}'")
        for address in self._data["address"]["name"]:
            # Essayer little endian (compatible avec l'architecture x86)
            MemoryReader.set_string(address, value, byteorder="little")
            print(f"[DEBUG Player] Name written to address {address} with little endian encoding")
            
    @property
    def money(self):
        return MemoryReader.get_i32(self._data["address"]["money"][0])
    
    @money.setter
    def money(self, value):
        for address in self._data["address"]["money"]:
            MemoryReader.set_i32(address, value)
        label = "{:,}".format(value)
        for address in self._data["address"]["money_label"]:
            MemoryReader.set_string(address + 4, label)
            
    @property
    def goto(self):
        return MemoryReader.get_byte(self._data["address"]["goto"][0])
    
    @goto.setter
    def goto(self, value):
        for address in self._data["address"]["goto"]:
            MemoryReader.set_byte(address, value)
            
    @property
    def position(self):
        return MemoryReader.get_byte(self._data["address"]["position"][0])
    
    @position.setter
    def position(self, value):
        for address in self._data["address"]["position"]:
            MemoryReader.set_byte(address, value)
