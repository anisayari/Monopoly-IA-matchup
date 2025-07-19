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
        
        # Debug désactivé pour réduire le spam
        # print(f"[DEBUG DynamicArrayAttribute] Reading array at offset 0x{self.offset:X} (address: 0x{base_address:X}), length: {length}")
        
        # Vérifier que la longueur est raisonnable
        if length < 0 or length > 100:
            # print(f"[WARNING] Array length seems invalid: {length}, trying alternative reading method")
            
            # Essayer de lire comme un pointeur vers un tableau
            pointer_address = MemoryReader.get_i32(base_address)
            if pointer_address > 0x10000000 and pointer_address < 0xFFFFFFFF:
                # print(f"[DEBUG] Trying as pointer: 0x{pointer_address:X}")
                try:
                    # Lire la longueur depuis le pointeur
                    alt_length = MemoryReader.get_i32(pointer_address)
                    if 0 <= alt_length <= 50:
                        # print(f"[DEBUG] Alternative length found: {alt_length}")
                        result = []
                        for i in range(alt_length):
                            element_address = MemoryReader.get_i32(pointer_address + 4 + i * 4)
                            if self.factory:
                                try:
                                    element = self.factory(element_address)
                                    result.append(element)
                                except:
                                    pass
                        return result
                except:
                    pass
            
            return []
        
        # Lire chaque élément
        result = []
        for i in range(length):
            element_address = MemoryReader.get_i32(base_address + 4 + i * 4)
            # print(f"[DEBUG] Element {i}: address 0x{element_address:X}")
            
            if self.factory:
                try:
                    element = self.factory(element_address)
                    result.append(element)
                except Exception as e:
                    # print(f"[ERROR] Failed to create element {i}: {e}")
                    pass
            else:
                result.append(element_address)
        
        return result