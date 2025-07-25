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
    
    @staticmethod
    def check_you_owe(addr: Hex = 0x90083E99) -> bool:
        """
        Vérifie si la string "You owe" est présente dans une plage d'adresses
        Retourne True si trouvée, False sinon
        """
        try:
            base_addr = MemoryReader.hex_to_int(addr)
            # Scanner une plage de 0x100 bytes (256 bytes) à partir de l'adresse de base
            scan_range = 0x100
            
            # Lire toute la plage en une seule fois
            chunk = dme.read_bytes(base_addr, scan_range)
            
            # Chercher "You owe" en UTF-16LE dans le chunk
            search_pattern = "You owe".encode("utf-16-le")
            
            if search_pattern in chunk:
                # Trouver la position exacte
                offset = chunk.find(search_pattern)
                found_addr = base_addr + offset
                
                # Lire la string complète à cette position
                string_at_addr = MemoryReader.get_string(found_addr, max_length=50, byteorder="little")
                
                print(f"[You Owe Check] You owe: True - Found at 0x{found_addr:08X}")
                print(f"[You Owe Check] Found string: '{string_at_addr}'")
                return True
            else:
                print(f"[You Owe Check] You owe: False - Not found in range 0x{base_addr:08X}-0x{base_addr + scan_range:08X}")
                return False
                
        except Exception as e:
            print(f"[You Owe Check] Error scanning range starting at 0x{base_addr:08X}: {e}")
            return False
    