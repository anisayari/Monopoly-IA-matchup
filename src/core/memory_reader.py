import dolphin_memory_engine as dme
from typing import Union

Hex = Union[str, int]

class MemoryReader:
    
    @staticmethod
    def hex_to_int(value: Hex) -> int:
        return int(value, 16) if isinstance(value, str) else value
    
    @staticmethod
    def set_string(addr: Hex, str: str, byteorder: str = "big") -> None:
        dme.write_bytes(MemoryReader.hex_to_int(addr), str.encode("utf-16-le" if byteorder == "little" else "utf-16-be") + b'\x00\x00')

    @staticmethod
    def get_string(addr: Hex, max_length = 1024, byteorder: str = "big") -> str:
        string = ""
        parsed_addr = MemoryReader.hex_to_int(addr)
        # Désactiver les logs pour éviter le spam
        # print(f"[DEBUG MemoryReader] Reading string from address 0x{parsed_addr:08X}, byteorder={byteorder}")
        i = 0
        while i < max_length:
            char = dme.read_bytes(parsed_addr, 2)
            if char == b"\x00\x00":
                break
            try:
                decoded = char.decode("utf-16-le" if byteorder == "little" else "utf-16-be")
                string += decoded
                # Désactiver les logs verbeux
                # if i < 10:  # Log first few chars
                #     print(f"[DEBUG MemoryReader] Char {i}: {char.hex()} -> '{decoded}'")
            except Exception as e:
                string += "?"
                # Désactiver les logs d'erreur qui spamment
                # print(f"[DEBUG MemoryReader] Failed to decode char at offset {i}: {char.hex()}, error: {e}")
            parsed_addr += 2
            i += 1
        # Désactiver le log final
        # print(f"[DEBUG MemoryReader] Final string: '{string}' (length: {len(string)})")
        return string
    
    
    @staticmethod
    def get_str(addr: Hex) -> str:
        return MemoryReader.get_string(
            MemoryReader.hex_to_int(addr) + 4, 
            MemoryReader.get_i32(addr), 
            "big"
        )
    
    @staticmethod
    def set_str(addr: Hex, value: str) -> None:
        addr = MemoryReader.hex_to_int(addr)
        MemoryReader.set_i32(addr, len(value))
        MemoryReader.set_string(addr + 4, value)
    
    @staticmethod
    def set_i16(addr: Hex, value: int, byteorder = "big") -> None:
        dme.write_bytes(MemoryReader.hex_to_int(addr), value.to_bytes(2, byteorder))
        
    @staticmethod
    def get_i16(addr: int, byteorder = "big") -> int:
        return int.from_bytes(dme.read_bytes(MemoryReader.hex_to_int(addr), 2), byteorder)
    
    @staticmethod
    def set_i32(addr: int, value: int, byteorder = "big") -> None:
        dme.write_bytes(MemoryReader.hex_to_int(addr), value.to_bytes(4, byteorder))

    @staticmethod
    def get_i32(addr: int, byteorder = "big") -> int:
        return int.from_bytes(dme.read_bytes(MemoryReader.hex_to_int(addr), 4), byteorder)
    
    @staticmethod
    def get_byte(addr: int, byteorder = "big") -> int:
        return int.from_bytes(dme.read_bytes(MemoryReader.hex_to_int(addr), 1), byteorder)

    @staticmethod
    def set_byte(addr: int, value: int, byteorder = "big") -> None:
        dme.write_bytes(MemoryReader.hex_to_int(addr), value.to_bytes(1, byteorder))
        
    @staticmethod
    def get_bytes(addr: int, length: int) -> bytes:
        return dme.read_bytes(MemoryReader.hex_to_int(addr), length)
    
    @staticmethod
    def set_bytes(addr: int, value: bytes) -> None:
        dme.write_bytes(MemoryReader.hex_to_int(addr), value)
    