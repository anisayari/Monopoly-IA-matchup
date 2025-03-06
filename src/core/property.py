from .memory_reader import MemoryReader

class Property:
    def __init__(self, base):
        self._base = base

    @property
    def name(self):
        return MemoryReader.get_string(self._base + 8)
    
    @property
    def position(self):
        return MemoryReader.get_i32(self._base + 0x48)
    
    @property
    def price(self):
        return MemoryReader.get_i32(self._base + 0x64)

    @property
    def rents(self):
        ptr = self._base + 0x74
        prices = []
        for i in range(6):
            prices.append(MemoryReader.get_i32(ptr + i * 4))
        return prices