from .game_loader import PlayerData
from .properties import Properties
from .memory_reader import MemoryReader

class Player:
    
    _data: PlayerData
    
    def __init__(self, data: PlayerData):
        self._data = data
        
    
    @property
    def id(self):
        return self._data["id"]

    
    @property
    def dices(self) -> list[int]:
        dices = []
        for dice in self._data["address"]["dices"]:
            dices.append(MemoryReader.get_byte(dice[0]))
        return dices
    
    @dices.setter
    def dices(self, value: list[int]):
        for dice in self._data["address"]["dices"]:
            v = value.pop(0)
            for address in dice:
                MemoryReader.set_byte(address, v)
    

    @property
    def roll(self):
        return MemoryReader.get_byte(self._data["address"]["roll"][0])
    
    @roll.setter
    def roll(self, value):
        for address in self._data["address"]["roll"]:
            MemoryReader.set_byte(address, value)
    
    @property
    def name(self):
        return MemoryReader.get_string(self._data["address"]["name"][0])
    
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
            MemoryReader.set_string(address, label)
            
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
