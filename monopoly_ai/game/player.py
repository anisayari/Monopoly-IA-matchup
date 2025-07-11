"""Player class for Monopoly game."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Player:
    """Represents a player in the game."""
    id: int
    name: str
    cash: int = 1500  # Starting cash
    position: int = 0  # Current board position
    properties: List[int] = field(default_factory=list)  # List of owned property positions
    in_jail: bool = False
    jail_turns: int = 0
    get_out_of_jail_cards: int = 0
    is_ai: bool = False
    bankrupt: bool = False
    
    def pay(self, amount: int) -> bool:
        """Pay an amount. Returns True if successful, False if insufficient funds."""
        if self.cash >= amount:
            self.cash -= amount
            return True
        return False
    
    def receive(self, amount: int):
        """Receive money."""
        self.cash += amount
    
    def move_to(self, position: int, pass_go_bonus: int = 200):
        """Move to a specific position, collecting GO bonus if passed."""
        if position < self.position and position != 10:  # Passed GO (except when going to jail)
            self.receive(pass_go_bonus)
            print(f"{self.name} passed GO and collected ${pass_go_bonus}")
        self.position = position
    
    def go_to_jail(self):
        """Send player to jail."""
        self.position = 10
        self.in_jail = True
        self.jail_turns = 0
        print(f"{self.name} goes to jail!")
    
    def get_out_of_jail(self):
        """Release player from jail."""
        self.in_jail = False
        self.jail_turns = 0
        print(f"{self.name} gets out of jail!")
    
    @property
    def net_worth(self) -> int:
        """Calculate total net worth (cash + property values)."""
        # TODO: Add property values
        return self.cash