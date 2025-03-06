from typing import List
import re
from .memory_reader import MemoryReader
from ..game.game import MonopolyGame
from .game_loader import GameLoader

class MessageFinder:
    
    def byte_process_player_names(game: MonopolyGame, text: str, args: List[str]) -> str:
        return b"(?:" + b"|".join([player.name.encode("utf-16-be") for player in game.players]) + b")"
    
    @staticmethod
    def messages(game: MonopolyGame) -> List[dict]:
        address_range: List[int, int] = list(map(GameLoader.to_hex, game.data.manifest["messages"]["address_range"]))
        memory_dump = MemoryReader.get_bytes(address_range[0], address_range[1] - address_range[0])
        
        results = []
             
        # for each event in the manifest
        for event in game.data.manifest["messages"]["events"]:
            
            # get the text to search
            str_text = MemoryReader.get_str(event["address"]) if event["type"] == "address" else event["pattern"]
            
            # convert regex symbols to true symbols (for the regext not use ? as a regex symbol)
            
            if "string_replace" in event:
                for key, value in event["string_replace"].items():
                    split = value.split(":")
                    if split[0] == "value":
                        str_text = str_text.replace(key, "".join(split[1:]))
                    elif split[0] == "process":
                        value = getattr(MessageFinder, "string_process_" + split[1])(game, str_text, split[2:])
                        str_text = str_text.replace(key, value)
            
            # convert string to bytes
            byte_text = str_text.encode("utf-16-be")
            
            # Escape special regex characters in byte_text
            byte_text = re.escape(byte_text)
            
            if "byte_replace" in event:
                for key, value in event["byte_replace"].items():
                    split = value.split(":")
                    if split[0] == "value":
                        byte_text = byte_text.replace(key.encode("utf-16-be"), "".join(split[1:]).encode("utf-8"))
                    elif split[0] == "process":
                        value = getattr(MessageFinder, "byte_process_" + split[1])(game, str_text, split[2:])
                        byte_text = byte_text.replace(key.encode("utf-16-be"), value)
                
            # Replace all occurrences of %<number> with (.*) using regex
            byte_text = re.sub(b'\x00%\x00\d', b'(.+)', byte_text)
            
            # convert pattern to regex
            try:
                pattern = re.compile(byte_text)
            except:
                continue
            # find all matches
            address = []
            
            # for each match, get the address and the text
            for match in pattern.finditer(memory_dump):
                index = address_range[0] + match.start() - 4
                address.append({
                    "address": hex(index),
                    "text": MemoryReader.get_str(index)
                })
    
                
            results.append({
                "id": event["id"],
                "data": address
            })
                  
        return results