from typing import Tuple, List, Dict
from collections import deque
from datetime import datetime
from ..core.memory_reader import MemoryReader
from ..core.memory_addresses import MemoryAddresses
from .enums import PlayerColor

class Player:
    """Représente un joueur dans le jeu"""
    def __init__(self, color: PlayerColor):
        self.color = color
        self._addresses = MemoryAddresses.ADDRESSES
        
        # Attributs de suivi
        self._current_money = 0
        self._last_position = 0
        self._transactions = deque(maxlen=50)  # Garde les 50 dernières transactions
        
        # Initialisation des valeurs
        self._update_current_money()
        self._update_last_position()

    def _update_current_money(self):
        """Met à jour l'argent actuel"""
        new_money = self.money
        if new_money != self._current_money:
            change = new_money - self._current_money
            if change != 0:
                self._transactions.append({
                    'time': datetime.now(),
                    'type': 'money',
                    'change': change,
                    'new_total': new_money
                })
            self._current_money = new_money

    def _update_last_position(self):
        """Met à jour la dernière position connue"""
        new_position = self.position
        if new_position != self._last_position:
            self._transactions.append({
                'time': datetime.now(),
                'type': 'position',
                'old_position': self._last_position,
                'new_position': new_position
            })
            self._last_position = new_position

    @property
    def current_money(self) -> int:
        """Retourne l'argent actuel du joueur"""
        self._update_current_money()
        return self._current_money

    @property
    def last_position(self) -> int:
        """Retourne la dernière position connue du joueur"""
        self._update_last_position()
        return self._last_position

    @property
    def transactions(self) -> List[Dict]:
        """Retourne l'historique des transactions"""
        return list(self._transactions)

    @property
    def label(self) -> str:
        """Récupère le nom du joueur"""
        addr = self._addresses[f"{self.color.value}_LABEL"][0]
        return MemoryReader.get_string(addr)

    @label.setter
    def label(self, value: str) -> None:
        """Définit le nom du joueur"""
        for addr in self._addresses[f"{self.color.value}_LABEL"]:
            MemoryReader.set_string(addr, value)

    @property
    def name(self) -> str:
        """Alias pour label - Récupère le nom du joueur"""
        return self.label

    @name.setter
    def name(self, value: str) -> None:
        """Alias pour label - Définit le nom du joueur"""
        self.label = value

    @property
    def money(self) -> int:
        """Argent du joueur"""
        addr = self._addresses[f"{self.color.value}_MONEY"][0]
        return MemoryReader.get_short(addr)

    @money.setter
    def money(self, value: int) -> None:
        """Définit l'argent du joueur"""
        old_money = self.money
        for addr in self._addresses[f"{self.color.value}_MONEY"]:
            MemoryReader.set_short(addr, value)
        for addr in self._addresses[f"{self.color.value}_MONEY_LABEL"]:
            MemoryReader.set_string(addr, str(value))
        
        # Mettre à jour le suivi
        if value != old_money:
            self._current_money = value
            self._transactions.append({
                'time': datetime.now(),
                'type': 'money',
                'change': value - old_money,
                'new_total': value
            })

    @property
    def position(self) -> int:
        """Position actuelle du joueur sur le plateau"""
        addr = self._addresses[f"{self.color.value}_POSITION"][0]
        pos = MemoryReader.get_byte(addr)
        
        # Mettre à jour le suivi si la position a changé
        if pos != self._last_position:
            self._last_position = pos
            self._transactions.append({
                'time': datetime.now(),
                'type': 'position',
                'old_position': self._last_position,
                'new_position': pos
            })
        
        return pos

    @property
    def goto(self) -> int:
        """Position cible du joueur"""
        addr = self._addresses[f"{self.color.value}_GOTO"][0]
        return MemoryReader.get_byte(addr)

    @property
    def dices(self) -> Tuple[int, int]:
        """Valeurs des dés du joueur"""
        addr1 = self._addresses[f"{self.color.value}_DICE_1"][0]
        addr2 = self._addresses[f"{self.color.value}_DICE_2"][0]
        return (MemoryReader.get_byte(addr1), MemoryReader.get_byte(addr2))

    @property
    def dice_sum(self) -> int:
        """Somme des dés du joueur"""
        addr = self._addresses[f"{self.color.value}_DICE_SUM"][0]
        return MemoryReader.get_byte(addr) 