from typing import List
import dolphin_memory_engine as dme

from ..core.memory_reader import MemoryReader
from ..core.game_loader import GameLoader
from ..core.player import Player
from ..core.auction import Auction

class MonopolyGame:
    """Classe principale gérant le jeu Monopoly"""
    
    _data: GameLoader
    _players: List[Player]
    _auction: Auction
    static_colors = ["red", "blue"]
    
    def __init__(self, data):
        """Initialise le jeu Monopoly"""
        
        # Initialiser les données pour le jeu
        self._data = data
        
        # Vérifier la connexion à Dolphin
        if not dme.is_hooked():
            dme.hook()
        if not dme.is_hooked():
            raise Exception("Impossible de se connecter à Dolphin Memory Engine")

        # Charger les joueurs
        self._players = []
        for player in self._data.manifest["players"]:
            self._players.append(Player(player))

        # Charger les cases
        self._squares = []

        # Auction
        self._auction = Auction(MemoryReader.hex_to_int(self._data.manifest["auction"]))
        
    @property
    def auction(self) -> Auction:
        """Renvoie l'instance de l'enchère"""
        return self._auction

    @property
    def players(self) -> List[Player]:
        """Renvoie la liste des joueurs"""
        return self._players
    
    @players.setter
    def players(self, value: List[Player]):
        """Définit la liste des joueurs"""
        self._players = value
        
    def get_player_by_id(self, player_id: str) -> Player:
        """Renvoie un joueur par son ID"""
        for player in self._players:
            if player.id == player_id:
                return player
        return None
    
    def get_player_by_name(self, player_name: str) -> Player:
        """Renvoie un joueur par son nom"""
        for player in self._players:
            if player.name == player_name:
                return player
        return None
        
    @property
    def data(self) -> GameLoader:
        """Renvoie les données du jeu"""
        return self._data
    
    @data.setter
    def data(self, value: GameLoader):
        """Définit les données du jeu"""
        self._data = value
        
    @property
    def properties(self):
        data = MemoryReader.get_bytes(
            MemoryReader.hex_to_int(self._data.manifest["properties"]["address_range"][0]),
            MemoryReader.hex_to_int(self._data.manifest["properties"]["address_range"][1]) - MemoryReader.hex_to_int(self._data.manifest["properties"]["address_range"][0])
        )

        lines = str(data)[2:-1].split("\\r\\n")
        cols = []
        for line in lines:
            cols.append(line.split(","))

        res = []
        for col in cols:
            re = {}
            for i in range(len(col)):
                re[cols[0][i].strip().lower()] = col[i].strip()
            res.append(re)
            
        out = []
        for r in res[1:]:
            o = {"rents": []}
            for k, v in r.items():
                if k == "hybridname":
                    o["id"] = int(v[8:])
                elif k == "property":
                    o["name"] = v
                elif k == "value":
                    o["price"] = int(v if v != "" else -1)
                elif k == "mortgage":
                    o["mortgage"] = int(v if v != "" else -1)
                elif k == "housecost":
                    o["cost"] = int(v if v != "" else -1)
                elif k.startswith("rent"):
                    i = int(k[4:])
                    while len(o["rents"]) < i:
                        o["rents"].append(-1)
                    if len(o["rents"]) == i:
                        o["rents"].append(int(v if v != "" else -1))
                    else:
                        o["rents"][i] = int(v if v != "" else -1)
            out.append(o)
            
        return out
    
    def get_property_by_id(self, prop_id: int):
        for prop in self.properties:
            if prop["id"] == prop_id:
                return prop
        return None
            
    def get_property_by_name(self, prop_name: str):
        for prop in self.properties:
            if prop["name"] == prop_name:
                return prop
        return None
    
    def get_property_by_player_id(self, player_id: str):
        player = self.get_player_by_id(player_id)
        if player is None:
            return None
        return self.get_property_by_id(player.goto)
        
    