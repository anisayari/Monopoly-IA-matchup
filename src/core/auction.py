from src.core.attributes import IntAttribute
from src.core.property import Property
from .game_loader import PlayerData
from .memory_reader import MemoryReader

class Auction:
    _base: int 

    current_price = IntAttribute(0x4)
    next_price = IntAttribute(0x8)
    current_bidder = IntAttribute(0xC)
    status = IntAttribute(0x14)

    def __init__(self, base):
        self._base = base

    def is_active(self):
        return self.status == 1