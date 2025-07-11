"""Auction system for Monopoly properties."""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import time
from utils.colors import *


@dataclass
class Bid:
    """Represents a bid in an auction."""
    player_id: int
    amount: int
    is_final: bool = False


class PropertyAuction:
    """Manages property auctions between players."""
    
    def __init__(self, property_square, players, manager, game):
        self.property = property_square
        self.players = players
        self.manager = manager
        self.game = game
        self.bids = {}  # player_id -> current bid
        self.bid_history = []
        self.active_bidders = [p.id for p in players if not p.bankrupt]
        self.min_increment = 10
        self.winner = None
        self.winning_bid = 0
        
    def run_auction(self):
        """Run the complete auction process."""
        print(f"\n{header('🏛️ AUCTION STARTING')} for {property_name(self.property.name)}")
        print(f"Base price: {money(self.property.price)}")
        print(divider("-", 60))
        
        # Phase 1: Secret initial bids
        self._collect_initial_bids()
        
        # Phase 2: Open bidding war
        if len([b for b in self.bids.values() if b > 0]) > 1:
            self._bidding_war()
        else:
            # Only one bidder or no bidders
            self._determine_winner()
        
        # Phase 3: Announce winner
        self._announce_winner()
        
        return self.winner, self.winning_bid
    
    def _collect_initial_bids(self):
        """Collect secret initial bids from all players."""
        print(f"\n{colored('📝 Secret bidding phase...', Colors.BRIGHT_CYAN)}")
        
        for player_id in self.active_bidders:
            player = self.players[player_id]
            
            # Get AI's initial bid
            bid_amount = self._get_initial_bid(player_id)
            self.bids[player_id] = bid_amount if bid_amount is not None else 0
            
            # Show thinking animation
            print(f"{player_name(player.name, player_id)} is evaluating the property...", end="")
            time.sleep(0.8)
            print(" ✓")
            
            # AI might comment on their strategy
            if bid_amount > 0:
                context = f"Making initial bid of ${bid_amount} for {self.property.name}"
            else:
                context = f"Deciding not to bid on {self.property.name}"
            
            comment = self.manager.enable_ai_chat(
                player_id, 
                self.game,
                context
            )
            if comment:
                print(f"💭 {player_name(player.name, player_id)}: {colored(comment, Colors.DIM)}")
        
        # Reveal initial bids
        print(f"\n{colored('📊 Initial bids revealed:', Colors.BRIGHT_YELLOW)}")
        for pid, bid in self.bids.items():
            player = self.players[pid]
            if bid > 0:
                print(f"  {player_name(player.name, pid)}: {money(bid)}")
            else:
                print(f"  {player_name(player.name, pid)}: {colored('Pass', Colors.DIM)}")
    
    def _get_initial_bid(self, player_id: int) -> int:
        """Get initial bid from AI."""
        options = {
            "property_name": self.property.name,
            "base_price": self.property.price,
            "property_color": self.property.color.value if hasattr(self.property, 'color') and self.property.color else None,
            "current_cash": self.players[player_id].cash,
            "max_bid_allowed": self.players[player_id].cash - 100  # Keep some reserve
        }
        
        bid = self.manager.make_decision(player_id, "auction_initial_bid", self.game, options)
        # Handle the result - it should be an integer
        if isinstance(bid, dict):
            bid = bid.get('bid_amount', 0)
        elif bid is None:
            bid = 0
        return max(0, min(int(bid), self.players[player_id].cash - 100))  # Ensure valid bid
    
    def _bidding_war(self):
        """Handle the open bidding war phase."""
        print(f"\n{colored('⚔️ BIDDING WAR BEGINS!', Colors.BRIGHT_RED + Colors.BOLD)}")
        print(divider("-", 60))
        
        # Get highest initial bidder
        current_high = max(self.bids.items(), key=lambda x: x[1])
        current_leader_id = current_high[0]
        current_high_bid = current_high[1]
        
        # Remove players who passed initially
        active = [pid for pid in self.active_bidders if self.bids[pid] > 0]
        
        round_num = 1
        while len(active) > 1:
            print(f"\n{colored(f'Round {round_num}:', Colors.BRIGHT_CYAN)}")
            print(f"Current high bid: {money(current_high_bid)} by {player_name(self.players[current_leader_id].name, current_leader_id)}")
            
            # Let other players respond
            still_active = []
            for pid in active:
                if pid == current_leader_id:
                    continue
                    
                player = self.players[pid]
                
                # Negotiate/taunt phase
                taunt = self.manager.enable_ai_chat(
                    current_leader_id,
                    self.game,
                    f"Leading auction at ${current_high_bid} for {self.property.name}"
                )
                if taunt:
                    print(f"\n💬 {player_name(self.players[current_leader_id].name, current_leader_id)}: {colored(taunt, GameColors.CHAT)}")
                    time.sleep(0.8)
                
                # Get response bid
                response = self._get_counter_bid(pid, current_high_bid, current_leader_id)
                
                if response > current_high_bid:
                    self.bids[pid] = response
                    print(f"\n🔥 {player_name(player.name, pid)} raises to {money(response)}!")
                    
                    # Reaction
                    reaction = self.manager.enable_ai_chat(
                        pid,
                        self.game,
                        f"Just raised bid to ${response} for {self.property.name}"
                    )
                    if reaction:
                        print(f"💬 {player_name(player.name, pid)}: {colored(reaction, GameColors.CHAT)}")
                    
                    still_active.append(pid)
                    current_leader_id = pid
                    current_high_bid = response
                else:
                    print(f"\n{player_name(player.name, pid)} {colored('drops out', Colors.DIM)}")
                    
                    # Farewell comment
                    farewell = self.manager.enable_ai_chat(
                        pid,
                        self.game,
                        f"Dropping out of auction for {self.property.name} at ${current_high_bid}"
                    )
                    if farewell:
                        print(f"💬 {player_name(player.name, pid)}: {colored(farewell, GameColors.CHAT)}")
                
                time.sleep(1)
            
            # Check if original leader wants to counter
            if still_active and current_leader_id not in still_active:
                # Original leader lost, do they want to counter?
                for pid in active:
                    if pid != current_leader_id and pid in still_active:
                        counter = self._get_counter_bid(current_leader_id, current_high_bid, pid)
                        if counter > current_high_bid:
                            self.bids[current_leader_id] = counter
                            print(f"\n🔥 {player_name(self.players[current_leader_id].name, current_leader_id)} counters with {money(counter)}!")
                            still_active.append(current_leader_id)
                            current_leader_id = current_leader_id
                            current_high_bid = counter
                        break
            
            active = [current_leader_id] + still_active
            active = list(set(active))  # Remove duplicates
            
            if len(active) == 1:
                break
                
            round_num += 1
            if round_num > 10:  # Prevent infinite loops
                print(colored("\n⏰ Auction time limit reached!", Colors.BRIGHT_YELLOW))
                break
        
        self.winner = current_leader_id
        self.winning_bid = current_high_bid
    
    def _get_counter_bid(self, player_id: int, current_high: int, leader_id: int) -> int:
        """Get counter bid from AI."""
        options = {
            "property_name": self.property.name,
            "current_high_bid": current_high,
            "current_leader": self.players[leader_id].name,
            "my_cash": self.players[player_id].cash,
            "my_last_bid": self.bids.get(player_id, 0),
            "min_raise": self.min_increment,
            "property_value": self.property.price
        }
        
        decision = self.manager.make_decision(player_id, "auction_counter_bid", self.game, options)
        
        if isinstance(decision, dict) and decision.get("bid"):
            return decision.get("new_bid", current_high + self.min_increment)
        return 0  # Drop out
    
    def _determine_winner(self):
        """Determine winner when there's no bidding war."""
        valid_bids = [(pid, bid) for pid, bid in self.bids.items() if bid > 0]
        
        if valid_bids:
            self.winner, self.winning_bid = max(valid_bids, key=lambda x: x[1])
        else:
            self.winner = None
            self.winning_bid = 0
    
    def _announce_winner(self):
        """Announce the auction winner."""
        print(f"\n{divider('=', 60)}")
        
        if self.winner is not None:
            winner = self.players[self.winner]
            print(f"🏆 {success(f'{player_name(winner.name, self.winner)} WINS the auction!')}")
            print(f"Winning bid: {money(self.winning_bid)} for {property_name(self.property.name)}")
            
            # Winner celebration
            celebration = self.manager.enable_ai_chat(
                self.winner,
                self.game,
                f"Won auction for {self.property.name} at ${self.winning_bid}!"
            )
            if celebration:
                print(f"\n💬 {player_name(winner.name, self.winner)}: {colored(celebration, GameColors.CHAT)}")
            
            # Loser reaction
            for pid in self.active_bidders:
                if pid != self.winner and self.bids.get(pid, 0) > 0:
                    reaction = self.manager.enable_ai_chat(
                        pid,
                        self.game,
                        f"Lost auction for {self.property.name} to {winner.name}"
                    )
                    if reaction:
                        print(f"💬 {player_name(self.players[pid].name, pid)}: {colored(reaction, GameColors.CHAT)}")
        else:
            print(f"❌ {colored('No winner - property remains unowned', Colors.DIM)}")
        
        print(divider('=', 60))