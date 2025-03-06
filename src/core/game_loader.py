import json
import typing
from .memory_reader import Hex
import re

class PlayerDataAddress(typing.TypedDict):
    name: typing.List[Hex]
    money: typing.List[Hex]
    money_label: typing.List[Hex]
    goto: typing.List[Hex]
    position: typing.List[Hex]
    base: Hex

class PlayerData(typing.TypedDict):
    id: str
    address: PlayerDataAddress

class MessageData(typing.TypedDict):
    id: str
    pattern: str

class Manifest(typing.TypedDict):
    players: typing.List[PlayerData]
    messages: typing.List[MessageData]
    auction: Hex

class GameLoader:
    
    _path_manifest: str
    _path_save: str
    
    def __init__(self, path_manifest, path_save):
        self._path_manifest = path_manifest
        self._path_save = path_save
        
    @property
    def manifest(self) -> Manifest:
        with open(self._path_manifest, 'r') as f:
            return json.loads(GameLoader.remove_comments("".join(f.readlines())))
    
    @staticmethod
    def to_hex(value: Hex) -> int:
        return int(value, 16) if isinstance(value, str) else value
    
    @staticmethod
    def remove_comments(string: str) -> str:
        return re.sub(r'//.*', '', string)
        