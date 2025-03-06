from .memory_reader import MemoryReader

class IntAttribute:
    def __init__(self, offset):
        self.offset = offset

    def __get__(self, instance, owner):
        if instance is None:
            return self
        base_address = instance._base + self.offset
        return MemoryReader.get_i32(base_address)

class StringAttribute:
    def __init__(self, offset):
        self.offset = offset

    def __get__(self, instance, owner):
        if instance is None:
            return self
        base_address = instance._base + self.offset
        return MemoryReader.get_string(base_address)
    
    def __set__(self, instance, value):
        base_address = instance._base + self.offset
        MemoryReader.set_string(base_address, value)

class OffsetAttribute:
    def __init__(self, offset, factory=None):
        self.offset = offset
        self.factory = factory or MemoryReader.get_i32

    def __get__(self, instance, owner):
        if instance is None:
            return self
        base_address = instance._base + self.offset
        return self.factory(base_address)
    
class FixedArrayAttribute:
    def __init__(self, offset, length):
        self.offset = offset
        self.length = length

    def __get__(self, instance, owner):
        if instance is None:
            return self
        base_address = instance._base + self.offset
        return [MemoryReader.get_i32(base_address + i * 4) for i in range(self.length)]

class DynamicArrayAttribute:
    def __init__(self, offset, factory=None):
        self.offset = offset
        self.factory = factory

    def __get__(self, instance, owner):
        if instance is None:
            return self
        base_address = instance._base + self.offset
        length = MemoryReader.get_i32(base_address)
        return [self.factory(MemoryReader.get_i32(base_address + 4 + i * 4)) for i in range(length)]