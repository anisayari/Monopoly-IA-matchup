"""Main Monopoly game engine."""
import random
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from .board import create_monopoly_board, Square, Property, SquareType, PropertyColor
from .player import Player
from .trade import TradingSystem, TradeOffer
try:
    from utils.colors import *
    USE_COLORS = True
except ImportError:
    # Fallback if colors not available
    USE_COLORS = False
    def colored(text, color): return text
    def money(amount): return f"${amount}"
    def player_name(name, id): return name
    def property_name(name, color=None): return name
    def action(text): return text
    def warning(text): return text
    def success(text): return text
    def dice(die1, die2): return f"{die1} + {die2} = {die1 + die2}"


@dataclass
class DiceRoll:
    die1: int
    die2: int
    
    @property
    def total(self) -> int:
        return self.die1 + self.die2
    
    @property
    def is_doubles(self) -> bool:
        return self.die1 == self.die2


class MonopolyGame:
    """Main game engine for Monopoly."""
    
    def __init__(self, player_names: List[str]):
        self.board = create_monopoly_board()
        self.players = [Player(i, name, is_ai=(i > 0)) for i, name in enumerate(player_names)]
        self.current_player_idx = 0
        self.turn_number = 0
        self.last_roll: Optional[DiceRoll] = None
        self.doubles_count = 0
        self.game_over = False
        self.trading_system = TradingSystem(self)
        
    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]
    
    def roll_dice(self, player_id: int) -> DiceRoll:
        """Roll two dice."""
        self.last_roll = DiceRoll(random.randint(1, 6), random.randint(1, 6))
        if USE_COLORS:
            print(f"{player_name(self.players[player_id].name, player_id)} rolls {dice(self.last_roll.die1, self.last_roll.die2)}")
        else:
            print(f"{self.players[player_id].name} rolls {self.last_roll.die1} + {self.last_roll.die2} = {self.last_roll.total}")
        return self.last_roll
    
    def move_player_token(self, player_id: int):
        """Move player based on last dice roll."""
        player = self.players[player_id]
        if self.last_roll:
            new_position = (player.position + self.last_roll.total) % 40
            player.move_to(new_position)
            square = self.board[new_position]
            if USE_COLORS:
                color_type = square.color.value if hasattr(square, 'color') and square.color else None
                print(f"{player_name(player.name, player_id)} lands on {property_name(square.name, color_type)}")
            else:
                print(f"{player.name} lands on {square.name}")
    
    def current_square(self, player_id: int) -> Square:
        """Get the square the player is currently on."""
        return self.board[self.players[player_id].position]
    
    def is_in_jail(self, player_id: int) -> bool:
        """Check if player is in jail."""
        return self.players[player_id].in_jail
    
    def has_get_out_card(self, player_id: int) -> bool:
        """Check if player has a get out of jail free card."""
        return self.players[player_id].get_out_of_jail_cards > 0
    
    def use_get_out_card(self, player_id: int):
        """Use a get out of jail free card."""
        player = self.players[player_id]
        if player.get_out_of_jail_cards > 0:
            player.get_out_of_jail_cards -= 1
            player.get_out_of_jail()
    
    def pay_bail(self, player_id: int):
        """Pay $50 to get out of jail."""
        player = self.players[player_id]
        if player.pay(50):
            player.get_out_of_jail()
            print(f"{player.name} pays $50 bail")
    
    def roll_for_doubles(self, player_id: int) -> bool:
        """Roll dice while in jail, checking for doubles."""
        roll = self.roll_dice(player_id)
        player = self.players[player_id]
        player.jail_turns += 1
        
        if roll.is_doubles:
            player.get_out_of_jail()
            return True
        elif player.jail_turns >= 3:
            # Forced to pay after 3 turns
            print(f"{player.name} must pay $50 after 3 turns in jail")
            if player.pay(50):
                player.get_out_of_jail()
            else:
                # TODO: Handle bankruptcy
                pass
        return False
    
    def get_property_owner(self, position: int) -> Optional[int]:
        """Get the owner of a property at a given position."""
        square = self.board[position]
        if isinstance(square, Property):
            return square.owner
        return None
    
    def buy_property(self, player_id: int):
        """Player buys the current property."""
        player = self.players[player_id]
        square = self.board[player.position]
        
        if isinstance(square, Property) and square.owner is None:
            if player.pay(square.price):
                square.owner = player_id
                player.properties.append(player.position)
                if USE_COLORS:
                    buy_msg = f"buys {property_name(square.name)} for {money(square.price)}"
                    print(f"{player_name(player.name, player_id)} {success(buy_msg)}")
                else:
                    print(f"{player.name} buys {square.name} for ${square.price}")
                return True
        return False
    
    def pay_rent(self, player_id: int):
        """Player pays rent on current property."""
        player = self.players[player_id]
        square = self.board[player.position]
        
        if isinstance(square, Property) and square.owner is not None and square.owner != player_id:
            owner = self.players[square.owner]
            rent = square.get_rent(self.last_roll.total if self.last_roll else None)
            
            if rent > 0:
                if player.pay(rent):
                    owner.receive(rent)
                    if USE_COLORS:
                        print(f"{player_name(player.name, player_id)} pays {money(rent)} rent to {player_name(owner.name, owner.id)}")
                    else:
                        print(f"{player.name} pays ${rent} rent to {owner.name}")
                else:
                    # Player can't afford rent
                    if USE_COLORS:
                        msg = f"{player_name(player.name, player_id)} can't afford {money(rent)} rent!"
                        print(warning(msg))
                    else:
                        print(f"{player.name} can't afford ${rent} rent!")
                    # TODO: Handle bankruptcy/mortgage
    
    def pay_tax(self, player_id: int):
        """Player pays tax."""
        player = self.players[player_id]
        square = self.board[player.position]
        
        if square.square_type == SquareType.TAX:
            tax_amount = 200 if square.position == 4 else 100  # Income tax or luxury tax
            if player.pay(tax_amount):
                print(f"{player.name} pays ${tax_amount} tax")
            else:
                print(f"{player.name} can't afford ${tax_amount} tax!")
                # TODO: Handle bankruptcy
    
    def execute_special_square(self, player_id: int):
        """Handle special squares like Chance, Community Chest, etc."""
        player = self.players[player_id]
        square = self.board[player.position]
        
        if square.square_type == SquareType.GO_TO_JAIL:
            player.go_to_jail()
        elif square.square_type in [SquareType.CHANCE, SquareType.COMMUNITY_CHEST]:
            # Simplified: just give/take random amount
            amount = random.choice([-100, -50, 50, 100, 200])
            if amount > 0:
                player.receive(amount)
                print(f"{player.name} receives ${amount} from {square.name}")
            else:
                if player.pay(-amount):
                    print(f"{player.name} pays ${-amount} from {square.name}")
    
    def start_auction(self, manager=None):
        """Start an auction for the current property."""
        square = self.board[self.current_player.position]
        
        if manager and isinstance(square, Property):
            from .auction import PropertyAuction
            auction = PropertyAuction(square, self.players, manager, self)
            winner_id, winning_bid = auction.run_auction()
            
            if winner_id is not None:
                # Process the winning bid
                winner = self.players[winner_id]
                if winner.pay(winning_bid):
                    square.owner = winner_id
                    winner.properties.append(square.position)
                    return True
        else:
            # Fallback to simple message
            print(f"Auction for {square.name} - no auction system available")
        
        return False
    
    def estimate_roi(self, player_id: int, price: int) -> float:
        """Estimate return on investment for a property."""
        # Simplified: always positive if player has enough cash buffer
        player = self.players[player_id]
        return 0.1 if player.cash > price + 500 else -0.1
    
    def mortgage_property(self, player_id: int, property_position: int) -> bool:
        """Mortgage a specific property."""
        player = self.players[player_id]
        square = self.board[property_position]
        
        if isinstance(square, Property) and square.owner == player_id and not square.mortgaged:
            mortgage_value = square.mortgage_value
            player.receive(mortgage_value)
            square.mortgaged = True
            if USE_COLORS:
                print(f"{player_name(player.name, player_id)} mortgages {property_name(square.name)} for {money(mortgage_value)}")
            else:
                print(f"{player.name} mortgages {square.name} for ${mortgage_value}")
            return True
        return False
    
    def unmortgage_property(self, player_id: int, property_position: int) -> bool:
        """Unmortgage a property (pay back loan + 10% interest)."""
        player = self.players[player_id]
        square = self.board[property_position]
        
        if isinstance(square, Property) and square.owner == player_id and square.mortgaged:
            unmortgage_cost = int(square.mortgage_value * 1.1)  # 10% interest
            if player.pay(unmortgage_cost):
                square.mortgaged = False
                if USE_COLORS:
                    print(f"{player_name(player.name, player_id)} unmortgages {property_name(square.name)} for {money(unmortgage_cost)}")
                else:
                    print(f"{player.name} unmortgages {square.name} for ${unmortgage_cost}")
                return True
        return False
    
    def get_mortgageable_properties(self, player_id: int) -> List[Dict]:
        """Get list of properties that can be mortgaged."""
        player = self.players[player_id]
        mortgageable = []
        
        for prop_pos in player.properties:
            square = self.board[prop_pos]
            if isinstance(square, Property) and not square.mortgaged:
                # Can't mortgage if houses are built
                if square.houses == 0:
                    mortgageable.append({
                        "position": prop_pos,
                        "name": square.name,
                        "mortgage_value": square.mortgage_value,
                        "color": square.color.value if hasattr(square, 'color') and square.color else None
                    })
        
        return mortgageable
    
    def mortgage_until_positive(self, player_id: int):
        """Mortgage properties until player has positive cash."""
        player = self.players[player_id]
        mortgageable = self.get_mortgageable_properties(player_id)
        
        for prop in mortgageable:
            if player.cash >= 0:
                break
            self.mortgage_property(player_id, prop["position"])
    
    def settle_negative_cash(self, player_id: int, creditor_id: Optional[int] = None):
        """Handle negative cash situations."""
        player = self.players[player_id]
        if player.cash < 0:
            if USE_COLORS:
                print(f"{warning(f'{player_name(player.name, player_id)} is bankrupt!')}")
            else:
                print(f"{player.name} is bankrupt!")
            player.bankrupt = True
            
            # Transfer properties to creditor
            if creditor_id is not None:
                creditor = self.players[creditor_id]
                for prop_pos in player.properties:
                    square = self.board[prop_pos]
                    if isinstance(square, Property):
                        square.owner = creditor_id
                        creditor.properties.append(prop_pos)
                        # Unmortgage transferred properties
                        square.mortgaged = False
                print(f"All properties transferred to {player_name(creditor.name, creditor_id) if USE_COLORS else creditor.name}")
            else:
                # Return to bank
                for prop_pos in player.properties:
                    square = self.board[prop_pos]
                    if isinstance(square, Property):
                        square.owner = None
                        square.mortgaged = False
            
            player.properties.clear()
    
    def has_monopoly(self, player_id: int, color: PropertyColor) -> bool:
        """Check if player has all properties of a color."""
        color_props = [sq for sq in self.board if isinstance(sq, Property) and sq.color == color]
        return all(prop.owner == player_id for prop in color_props)
    
    def has_full_monopoly(self, player_id: int) -> bool:
        """Check if player has any complete color group."""
        for color in PropertyColor:
            if self.has_monopoly(player_id, color):
                return True
        return False
    
    def detect_trade_opportunities(self, player_id: int) -> bool:
        """Detect if there are beneficial trade opportunities."""
        # Simplified: always false for now
        return False
    
    def evaluate_build_roi(self, player_id: int) -> bool:
        """Evaluate if building houses/hotels is worth it."""
        # Simplified: build if player has monopoly and enough cash
        player = self.players[player_id]
        return self.has_full_monopoly(player_id) and player.cash > 1000
    
    def build_houses_or_hotels(self, player_id: int):
        """Build houses or hotels on monopolies."""
        player = self.players[player_id]
        for color in PropertyColor:
            if self.has_monopoly(player_id, color):
                color_props = [sq for sq in self.board if isinstance(sq, Property) and sq.color == color]
                for prop in color_props:
                    if prop.houses < 5 and player.cash > prop.house_cost + 500:
                        if player.pay(prop.house_cost):
                            prop.houses += 1
                            house_type = "hotel" if prop.houses == 5 else f"{prop.houses} house(s)"
                            print(f"{player.name} builds {house_type} on {prop.name}")
                            break
    
    def find_best_trade_partner(self, player_id: int) -> Optional[int]:
        """Find the best player to trade with."""
        # Simplified: no trading for now
        return None
    
    def last_roll_was_doubles(self, player_id: int) -> bool:
        """Check if the last roll was doubles."""
        return self.last_roll.is_doubles if self.last_roll else False
    
    def send_player_to_jail(self, player_id: int):
        """Send a player to jail."""
        self.players[player_id].go_to_jail()
    
    def end_turn(self, player_id: int):
        """End the current player's turn."""
        player = self.players[player_id]
        if USE_COLORS:
            print(f"{player_name(player.name, player_id)} ends turn with {money(player.cash)}")
            print(divider("-", 50))
        else:
            print(f"{player.name} ends turn with ${player.cash}")
            print("-" * 50)
        
        # Check for game over
        active_players = [p for p in self.players if not p.bankrupt]
        if len(active_players) <= 1:
            self.game_over = True
            if active_players:
                print(f"\nGAME OVER! {active_players[0].name} wins!")
        else:
            # Move to next player
            self.doubles_count = 0
            self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
            while self.players[self.current_player_idx].bankrupt:
                self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
    
    def get_game_state(self) -> Dict:
        """Get current game state for AI."""
        return {
            'current_player': self.current_player_idx,
            'players': [
                {
                    'id': p.id,
                    'name': p.name,
                    'cash': p.cash,
                    'position': p.position,
                    'properties': p.properties,
                    'in_jail': p.in_jail,
                    'bankrupt': p.bankrupt
                }
                for p in self.players
            ],
            'board': [
                {
                    'position': sq.position,
                    'name': sq.name,
                    'type': sq.square_type.value,
                    'owner': sq.owner if isinstance(sq, Property) else None,
                    'price': sq.price if isinstance(sq, Property) else None,
                    'houses': sq.houses if isinstance(sq, Property) else None,
                    'mortgaged': sq.mortgaged if isinstance(sq, Property) else None
                }
                for sq in self.board
            ]
        }