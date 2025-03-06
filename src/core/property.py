from src.core.attributes import StringAttribute, IntAttribute, FixedArrayAttribute
from .memory_reader import MemoryReader

class Property:
    name = StringAttribute(0x8)
    position = IntAttribute(0x48)
    price = IntAttribute(0x64)
    rents = FixedArrayAttribute(0x74, 6)

    def __init__(self, base):
        self._base = base