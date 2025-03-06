

from .memory_reader import MemoryReader
from .property import Property


class Properties:
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __init__(self, base):
        self._base = base

    def  __len__(self):
        return MemoryReader.get_i32(self._base)

    def __getitem__(self, key):
        if key >= len(self):
            raise IndexError
        return Property(MemoryReader.get_i32(self._base + 4 + key * 4))