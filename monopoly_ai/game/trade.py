"""Trading system for Monopoly."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from utils.colors import *


@dataclass
class TradeOffer:
    """Represents a trade offer between players."""
    proposer_id: int
    recipient_id: int
    offer_properties: List[int]  # Property positions offered
    offer_cash: int
    request_properties: List[int]  # Property positions requested
    request_cash: int
    
    def describe(self, game) -> str:
        """Get a description of the trade offer."""
        proposer = game.players[self.proposer_id]
        recipient = game.players[self.recipient_id]
        
        parts = [f"{player_name(proposer.name, self.proposer_id)} offers:"]
        
        # What proposer offers
        if self.offer_properties:
            prop_names = [game.board[pos].name for pos in self.offer_properties]
            parts.append(f"  Properties: {', '.join(prop_names)}")
        if self.offer_cash > 0:
            parts.append(f"  Cash: {money(self.offer_cash)}")
        
        parts.append(f"\nTo {player_name(recipient.name, self.recipient_id)} for:")
        
        # What proposer wants
        if self.request_properties:
            prop_names = [game.board[pos].name for pos in self.request_properties]
            parts.append(f"  Properties: {', '.join(prop_names)}")
        if self.request_cash > 0:
            parts.append(f"  Cash: {money(self.request_cash)}")
        
        return "\n".join(parts)


class TradingSystem:
    """Manages trades between players."""
    
    def __init__(self, game):
        self.game = game
        self.pending_offers: List[TradeOffer] = []
        self.completed_trades: List[TradeOffer] = []
    
    def propose_trade(self, offer: TradeOffer, manager=None) -> bool:
        """Propose a trade to another player."""
        # Validate the trade
        if not self._validate_trade(offer):
            return False
        
        print(f"\n{header('💼 TRADE PROPOSAL')}")
        print(offer.describe(self.game))
        print(divider("-", 60))
        
        # If we have a manager, let AI decide
        if manager:
            # Add context for the decision
            context = self._get_trade_context(offer)
            
            # Let recipient AI decide
            decision = manager.make_decision(
                offer.recipient_id,
                "trade_response",
                self.game,
                {
                    "offer": {
                        "properties": [self.game.board[p].name for p in offer.offer_properties],
                        "cash": offer.offer_cash
                    },
                    "request": {
                        "properties": [self.game.board[p].name for p in offer.request_properties],
                        "cash": offer.request_cash
                    },
                    "proposer": self.game.players[offer.proposer_id].name,
                    "context": context
                }
            )
            
            # AI can accept, reject, or counter
            if isinstance(decision, dict):
                if decision.get("accept"):
                    print(f"\n✅ {success('Trade ACCEPTED!')}")
                    
                    # Let recipient comment
                    comment = manager.enable_ai_chat(
                        offer.recipient_id,
                        self.game,
                        f"Just accepted trade from {self.game.players[offer.proposer_id].name}"
                    )
                    if comment:
                        print(f"💬 {player_name(self.game.players[offer.recipient_id].name, offer.recipient_id)}: {colored(comment, GameColors.CHAT)}")
                    
                    self._execute_trade(offer)
                    return True
                    
                elif decision.get("counter_offer"):
                    print(f"\n🔄 {colored('Trade COUNTERED', Colors.BRIGHT_YELLOW)}")
                    # Create counter offer
                    counter = TradeOffer(
                        proposer_id=offer.recipient_id,
                        recipient_id=offer.proposer_id,
                        offer_properties=decision["counter_offer"].get("offer_properties", []),
                        offer_cash=decision["counter_offer"].get("offer_cash", 0),
                        request_properties=decision["counter_offer"].get("request_properties", []),
                        request_cash=decision["counter_offer"].get("request_cash", 0)
                    )
                    
                    # Recursive call for counter offer
                    return self.propose_trade(counter, manager)
                    
                else:
                    print(f"\n❌ {warning('Trade REJECTED')}")
                    
                    # Let recipient comment on rejection
                    comment = manager.enable_ai_chat(
                        offer.recipient_id,
                        self.game,
                        f"Just rejected trade from {self.game.players[offer.proposer_id].name}"
                    )
                    if comment:
                        print(f"💬 {player_name(self.game.players[offer.recipient_id].name, offer.recipient_id)}: {colored(comment, GameColors.CHAT)}")
                    
                    return False
            else:
                # Simple accept/reject
                if decision:
                    print(f"\n✅ {success('Trade ACCEPTED!')}")
                    self._execute_trade(offer)
                    return True
                else:
                    print(f"\n❌ {warning('Trade REJECTED')}")
                    return False
        
        # Without manager, just execute (for testing)
        self._execute_trade(offer)
        return True
    
    def _validate_trade(self, offer: TradeOffer) -> bool:
        """Validate that a trade is legal."""
        proposer = self.game.players[offer.proposer_id]
        recipient = self.game.players[offer.recipient_id]
        
        # Check cash
        if offer.offer_cash > proposer.cash:
            print(warning("Proposer doesn't have enough cash"))
            return False
        
        if offer.request_cash > recipient.cash:
            print(warning("Recipient doesn't have enough cash"))
            return False
        
        # Check property ownership
        for prop_pos in offer.offer_properties:
            square = self.game.board[prop_pos]
            if not hasattr(square, 'owner') or square.owner != offer.proposer_id:
                print(warning(f"Proposer doesn't own {square.name}"))
                return False
            # Can't trade mortgaged properties or properties with houses
            if square.mortgaged:
                print(warning(f"{square.name} is mortgaged"))
                return False
            if hasattr(square, 'houses') and square.houses > 0:
                print(warning(f"{square.name} has buildings"))
                return False
        
        for prop_pos in offer.request_properties:
            square = self.game.board[prop_pos]
            if not hasattr(square, 'owner') or square.owner != offer.recipient_id:
                print(warning(f"Recipient doesn't own {square.name}"))
                return False
            if square.mortgaged:
                print(warning(f"{square.name} is mortgaged"))
                return False
            if hasattr(square, 'houses') and square.houses > 0:
                print(warning(f"{square.name} has buildings"))
                return False
        
        return True
    
    def _execute_trade(self, offer: TradeOffer):
        """Execute a validated trade."""
        proposer = self.game.players[offer.proposer_id]
        recipient = self.game.players[offer.recipient_id]
        
        # Exchange cash
        if offer.offer_cash > 0:
            proposer.pay(offer.offer_cash)
            recipient.receive(offer.offer_cash)
        
        if offer.request_cash > 0:
            recipient.pay(offer.request_cash)
            proposer.receive(offer.request_cash)
        
        # Exchange properties
        for prop_pos in offer.offer_properties:
            square = self.game.board[prop_pos]
            square.owner = offer.recipient_id
            proposer.properties.remove(prop_pos)
            recipient.properties.append(prop_pos)
        
        for prop_pos in offer.request_properties:
            square = self.game.board[prop_pos]
            square.owner = offer.proposer_id
            recipient.properties.remove(prop_pos)
            proposer.properties.append(prop_pos)
        
        self.completed_trades.append(offer)
        
        print(f"\n{success('Trade completed successfully!')}")
        print(f"{player_name(proposer.name, proposer.id)} now has {money(proposer.cash)}")
        print(f"{player_name(recipient.name, recipient.id)} now has {money(recipient.cash)}")
    
    def _get_trade_context(self, offer: TradeOffer) -> Dict:
        """Get context about the trade for AI decision making."""
        context = {
            "monopoly_impact": self._check_monopoly_impact(offer),
            "value_assessment": self._assess_trade_value(offer),
            "strategic_value": self._assess_strategic_value(offer)
        }
        return context
    
    def _check_monopoly_impact(self, offer: TradeOffer) -> Dict:
        """Check if trade creates or breaks monopolies."""
        result = {
            "proposer_gains_monopoly": False,
            "recipient_gains_monopoly": False,
            "proposer_loses_monopoly": False,
            "recipient_loses_monopoly": False
        }
        
        # Check each property in the trade
        for prop_pos in offer.request_properties:
            square = self.game.board[prop_pos]
            if hasattr(square, 'color') and square.color:
                # Would proposer complete a monopoly?
                color_props = [s for s in self.game.board if hasattr(s, 'color') and s.color == square.color]
                owned_by_proposer = sum(1 for s in color_props if hasattr(s, 'owner') and s.owner == offer.proposer_id)
                if owned_by_proposer == len(color_props) - 1:
                    result["proposer_gains_monopoly"] = True
        
        # Similar checks for other scenarios...
        return result
    
    def _assess_trade_value(self, offer: TradeOffer) -> Dict:
        """Assess the monetary value of the trade."""
        proposer_value = offer.offer_cash
        recipient_value = offer.request_cash
        
        for prop_pos in offer.offer_properties:
            square = self.game.board[prop_pos]
            proposer_value += square.price
        
        for prop_pos in offer.request_properties:
            square = self.game.board[prop_pos]
            recipient_value += square.price
        
        return {
            "proposer_gives": proposer_value,
            "recipient_gives": recipient_value,
            "net_value": proposer_value - recipient_value
        }
    
    def _assess_strategic_value(self, offer: TradeOffer) -> Dict:
        """Assess strategic implications of the trade."""
        # Simplified assessment
        return {
            "creates_threat": False,
            "defensive_value": False,
            "offensive_value": False
        }