"""Monopoly board definition."""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class SquareType(Enum):
    PROPERTY = "property"
    RAILROAD = "railroad"
    UTILITY = "utility"
    TAX = "tax"
    SPECIAL = "special"
    GO = "go"
    JAIL = "jail"
    FREE_PARKING = "free_parking"
    GO_TO_JAIL = "go_to_jail"
    CHANCE = "chance"
    COMMUNITY_CHEST = "community_chest"


class PropertyColor(Enum):
    BROWN = "brown"
    LIGHT_BLUE = "light_blue"
    PINK = "pink"
    ORANGE = "orange"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    DARK_BLUE = "dark_blue"


@dataclass
class Square:
    """Base class for all board squares."""
    position: int
    name: str
    square_type: SquareType
    
    def is_property(self) -> bool:
        return self.square_type in [SquareType.PROPERTY, SquareType.RAILROAD, SquareType.UTILITY]
    
    def is_tax(self) -> bool:
        return self.square_type == SquareType.TAX
    
    def is_special(self) -> bool:
        return self.square_type in [SquareType.CHANCE, SquareType.COMMUNITY_CHEST, 
                                   SquareType.GO_TO_JAIL, SquareType.GO, 
                                   SquareType.JAIL, SquareType.FREE_PARKING]


@dataclass
class Property(Square):
    """Represents a property square."""
    price: int
    rent: List[int]  # [base, 1house, 2houses, 3houses, 4houses, hotel]
    house_cost: int
    owner: Optional[int] = None
    houses: int = 0
    mortgaged: bool = False
    color: Optional[PropertyColor] = None
    
    def __post_init__(self):
        if self.square_type == SquareType.PROPERTY:
            assert self.color is not None, "Properties must have a color"
    
    def get_rent(self, dice_roll: Optional[int] = None) -> int:
        """Calculate rent based on current state."""
        if self.mortgaged or self.owner is None:
            return 0
            
        if self.square_type == SquareType.UTILITY:
            # Utilities: 4x or 10x dice roll
            if dice_roll is None:
                return 0
            multiplier = 4  # TODO: check if owner has both utilities
            return multiplier * dice_roll
            
        elif self.square_type == SquareType.RAILROAD:
            # Railroads: 25, 50, 100, 200 based on number owned
            count = 1  # TODO: count railroads owned by player
            return 25 * (2 ** (count - 1))
            
        else:  # Regular property
            if self.houses == 0:
                # TODO: check for monopoly (double rent)
                return self.rent[0]
            else:
                return self.rent[min(self.houses, 5)]
    
    @property
    def mortgage_value(self) -> int:
        return self.price // 2


def create_monopoly_board() -> List[Square]:
    """Create a standard Monopoly board."""
    board = []
    
    # Simplified board with key properties
    board_data = [
        # Position 0: GO
        Square(0, "GO", SquareType.GO),
        
        # Brown properties
        Property(1, "Mediterranean Avenue", SquareType.PROPERTY, 60, [2, 10, 30, 90, 160, 250], 50, color=PropertyColor.BROWN),
        Square(2, "Community Chest", SquareType.COMMUNITY_CHEST),
        Property(3, "Baltic Avenue", SquareType.PROPERTY, 60, [4, 20, 60, 180, 320, 450], 50, color=PropertyColor.BROWN),
        Square(4, "Income Tax", SquareType.TAX),
        Property(5, "Reading Railroad", SquareType.RAILROAD, 200, [25, 50, 100, 200, 0, 0], 0),
        
        # Light blue properties
        Property(6, "Oriental Avenue", SquareType.PROPERTY, 100, [6, 30, 90, 270, 400, 550], 50, color=PropertyColor.LIGHT_BLUE),
        Square(7, "Chance", SquareType.CHANCE),
        Property(8, "Vermont Avenue", SquareType.PROPERTY, 100, [6, 30, 90, 270, 400, 550], 50, color=PropertyColor.LIGHT_BLUE),
        Property(9, "Connecticut Avenue", SquareType.PROPERTY, 120, [8, 40, 100, 300, 450, 600], 50, color=PropertyColor.LIGHT_BLUE),
        
        # Jail
        Square(10, "Jail/Just Visiting", SquareType.JAIL),
        
        # Pink properties
        Property(11, "St. Charles Place", SquareType.PROPERTY, 140, [10, 50, 150, 450, 625, 750], 100, color=PropertyColor.PINK),
        Property(12, "Electric Company", SquareType.UTILITY, 150, [0, 0, 0, 0, 0, 0], 0),
        Property(13, "States Avenue", SquareType.PROPERTY, 140, [10, 50, 150, 450, 625, 750], 100, color=PropertyColor.PINK),
        Property(14, "Virginia Avenue", SquareType.PROPERTY, 160, [12, 60, 180, 500, 700, 900], 100, color=PropertyColor.PINK),
        Property(15, "Pennsylvania Railroad", SquareType.RAILROAD, 200, [25, 50, 100, 200, 0, 0], 0),
        
        # Orange properties
        Property(16, "St. James Place", SquareType.PROPERTY, 180, [14, 70, 200, 550, 750, 950], 100, color=PropertyColor.ORANGE),
        Square(17, "Community Chest", SquareType.COMMUNITY_CHEST),
        Property(18, "Tennessee Avenue", SquareType.PROPERTY, 180, [14, 70, 200, 550, 750, 950], 100, color=PropertyColor.ORANGE),
        Property(19, "New York Avenue", SquareType.PROPERTY, 200, [16, 80, 220, 600, 800, 1000], 100, color=PropertyColor.ORANGE),
        
        # Free Parking
        Square(20, "Free Parking", SquareType.FREE_PARKING),
        
        # Red properties
        Property(21, "Kentucky Avenue", SquareType.PROPERTY, 220, [18, 90, 250, 700, 875, 1050], 150, color=PropertyColor.RED),
        Square(22, "Chance", SquareType.CHANCE),
        Property(23, "Indiana Avenue", SquareType.PROPERTY, 220, [18, 90, 250, 700, 875, 1050], 150, color=PropertyColor.RED),
        Property(24, "Illinois Avenue", SquareType.PROPERTY, 240, [20, 100, 300, 750, 925, 1100], 150, color=PropertyColor.RED),
        Property(25, "B&O Railroad", SquareType.RAILROAD, 200, [25, 50, 100, 200, 0, 0], 0),
        
        # Yellow properties
        Property(26, "Atlantic Avenue", SquareType.PROPERTY, 260, [22, 110, 330, 800, 975, 1150], 150, color=PropertyColor.YELLOW),
        Property(27, "Ventnor Avenue", SquareType.PROPERTY, 260, [22, 110, 330, 800, 975, 1150], 150, color=PropertyColor.YELLOW),
        Property(28, "Water Works", SquareType.UTILITY, 150, [0, 0, 0, 0, 0, 0], 0),
        Property(29, "Marvin Gardens", SquareType.PROPERTY, 280, [24, 120, 360, 850, 1025, 1200], 150, color=PropertyColor.YELLOW),
        
        # Go to jail
        Square(30, "Go To Jail", SquareType.GO_TO_JAIL),
        
        # Green properties
        Property(31, "Pacific Avenue", SquareType.PROPERTY, 300, [26, 130, 390, 900, 1100, 1275], 200, color=PropertyColor.GREEN),
        Property(32, "North Carolina Avenue", SquareType.PROPERTY, 300, [26, 130, 390, 900, 1100, 1275], 200, color=PropertyColor.GREEN),
        Square(33, "Community Chest", SquareType.COMMUNITY_CHEST),
        Property(34, "Pennsylvania Avenue", SquareType.PROPERTY, 320, [28, 150, 450, 1000, 1200, 1400], 200, color=PropertyColor.GREEN),
        Property(35, "Short Line Railroad", SquareType.RAILROAD, 200, [25, 50, 100, 200, 0, 0], 0),
        
        # Chance
        Square(36, "Chance", SquareType.CHANCE),
        
        # Dark blue properties
        Property(37, "Park Place", SquareType.PROPERTY, 350, [35, 175, 500, 1100, 1300, 1500], 200, color=PropertyColor.DARK_BLUE),
        Square(38, "Luxury Tax", SquareType.TAX),
        Property(39, "Boardwalk", SquareType.PROPERTY, 400, [50, 200, 600, 1400, 1700, 2000], 200, color=PropertyColor.DARK_BLUE),
    ]
    
    return board_data