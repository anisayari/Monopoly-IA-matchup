from src.core.attributes import DynamicArrayAttribute, IntAttribute
from src.core.property import Property
from .game_loader import PlayerData
from .memory_reader import MemoryReader

class Player:
    _data: PlayerData

    dice1 = IntAttribute(0x0)
    dice2 = IntAttribute(0x4)
    roll = IntAttribute(0x10)
    properties = DynamicArrayAttribute(0x144, Property)
    
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
        return MemoryReader.get_string(self._data["address"]["name"][0], max_length=10)
    
    @name.setter
    def name(self, value):
        for address in self._data["address"]["name"]:
            MemoryReader.set_string(address, value)
            
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
