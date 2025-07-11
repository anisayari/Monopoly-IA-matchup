"""
GameEventListener - Listens to real game events and detects when AI decisions are needed.

This module connects to the existing listener system and translates game events
into AI-understandable decision points.
"""

import json
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import time
import threading

if TYPE_CHECKING:
    from src.game.monopoly import MonopolyGame

try:
    from .web_notifier import web_notifier
except ImportError:
    web_notifier = None


class DecisionType(Enum):
    """Types of decisions the AI needs to make."""
    BUY_PROPERTY = "buy_property"
    JAIL_STRATEGY = "jail_strategy"
    BUILD_HOUSES = "build_houses"
    MORTGAGE_PROPERTY = "mortgage_property"
    TRADE_OFFER = "trade_offer"
    TRADE_RESPONSE = "trade_response"
    AUCTION_BID = "auction_bid"
    GENERAL_ACTION = "general_action"
    ROLL_DICE = "roll_dice"


@dataclass
class DecisionContext:
    """Context for a decision that needs to be made."""
    decision_type: DecisionType
    player_id: int
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    message: Optional[str] = None
    requires_immediate_response: bool = True


class GameEventListener:
    """
    Listens to game events and detects when AI decisions are needed.
    
    Connects to the existing MonopolyListeners system without modifying it.
    """
    
    def __init__(self, monopoly_game):
        """
        Initialize the GameEventListener.
        
        Args:
            monopoly_game: The MonopolyGame instance from src/game/monopoly.py
        """
        self.game = monopoly_game
        self.listeners = monopoly_game.listeners
        self.contexte = monopoly_game.contexte
        
        # Callback for when a decision is needed
        self.on_decision_needed: Optional[Callable[[DecisionContext], None]] = None
        
        # Track current state
        self.current_player_turn = None
        self.pending_decision = None
        self.auction_active = False
        
        # Message patterns that indicate decisions are needed
        self.decision_patterns = {
            # Property purchase
            "want_to_buy": DecisionType.BUY_PROPERTY,
            "buy_house_prompt": DecisionType.BUY_PROPERTY,
            "want_to_buy_square": DecisionType.BUY_PROPERTY,
            
            # Jail
            "pay_the_bail": DecisionType.JAIL_STRATEGY,
            "use_jail_free_card": DecisionType.JAIL_STRATEGY,
            "pay_jail_fine_prompt": DecisionType.JAIL_STRATEGY,
            
            # Building
            "buy_house": DecisionType.BUILD_HOUSES,
            "sell_house_prompt": DecisionType.BUILD_HOUSES,
            
            # Mortgage
            "mortgage": DecisionType.MORTGAGE_PROPERTY,
            "unmortgage": DecisionType.MORTGAGE_PROPERTY,
            
            # Trading
            "trade": DecisionType.TRADE_OFFER,
            "add_to_deal": DecisionType.TRADE_OFFER,
            
            # Auction
            "bid_for_property": DecisionType.AUCTION_BID,
            "to_bid_instructions": DecisionType.AUCTION_BID,
            "current_bid": DecisionType.AUCTION_BID,
            
            # General actions
            "what_would_you_like_to_do": DecisionType.GENERAL_ACTION,
            "roll_again": DecisionType.ROLL_DICE,
        }
        
        self._setup_listeners()
    
    def _setup_listeners(self):
        """Set up event listeners for game events."""
        # Listen to messages - these indicate decision points
        self.listeners.on("message_added", self._on_message_added)
        
        # Listen to auction events
        self.listeners.on("auction_started", self._on_auction_started)
        self.listeners.on("auction_ended", self._on_auction_ended)
        self.listeners.on("auction_bid", self._on_auction_bid)
        
        # Listen to player events to track turn
        self.listeners.on("player_dice_changed", self._on_dice_changed)
        
        # Listen to context events for higher-level decisions
        if hasattr(self.contexte, 'event_history'):
            # Monitor context changes through polling (alternative approach)
            self._start_context_monitor()
    
    def _on_message_added(self, message_data: Dict[str, Any]):
        """Handle new messages from the game."""
        message = message_data.get('message', '')
        group = message_data.get('group', '')
        
        # Send to web interface
        if web_notifier:
            web_notifier.send_event(
                event_type="message",
                message=message,
                player=self._get_current_player(),
                data=message_data
            )
        
        # Check if this message indicates a decision is needed
        decision_type = self._detect_decision_type(message, group)
        
        if decision_type:
            # Extract relevant context based on message type
            context = self._build_decision_context(decision_type, message, message_data)
            
            # Notify that a decision is needed
            if self.on_decision_needed:
                self.on_decision_needed(context)
    
    def _detect_decision_type(self, message: str, group: str) -> Optional[DecisionType]:
        """Detect if a message indicates a decision is needed."""
        message_lower = message.lower()
        
        # Check patterns
        for pattern, decision_type in self.decision_patterns.items():
            if pattern in message_lower:
                return decision_type
        
        # Check group-based decisions
        if group == "property_offer":
            return DecisionType.BUY_PROPERTY
        elif group == "jail_options":
            return DecisionType.JAIL_STRATEGY
        
        return None
    
    def _build_decision_context(self, decision_type: DecisionType, 
                               message: str, message_data: Dict[str, Any]) -> DecisionContext:
        """Build context for the decision."""
        # Get current player from context
        current_player = self._get_current_player()
        
        context = DecisionContext(
            decision_type=decision_type,
            player_id=current_player,
            message=message,
            data={
                'message_data': message_data,
                'game_state': self._get_game_state(),
            }
        )
        
        # Add specific data based on decision type
        if decision_type == DecisionType.BUY_PROPERTY:
            context.data['property'] = self._extract_property_from_message(message)
        elif decision_type == DecisionType.AUCTION_BID:
            context.data['current_bid'] = self._extract_bid_from_message(message)
            context.data['auction_property'] = self.auction_active
        
        return context
    
    def _on_auction_started(self, auction_data: Dict[str, Any]):
        """Handle auction start event."""
        self.auction_active = True
        
        # Auction always requires immediate decision
        context = DecisionContext(
            decision_type=DecisionType.AUCTION_BID,
            player_id=self._get_current_player(),
            data={
                'auction_data': auction_data,
                'game_state': self._get_game_state(),
            }
        )
        
        if self.on_decision_needed:
            self.on_decision_needed(context)
    
    def _on_auction_ended(self, auction_data: Dict[str, Any]):
        """Handle auction end event."""
        self.auction_active = False
    
    def _on_auction_bid(self, bid_data: Dict[str, Any]):
        """Handle auction bid event."""
        # May need to respond with counter-bid
        if self.auction_active:
            context = DecisionContext(
                decision_type=DecisionType.AUCTION_BID,
                player_id=self._get_current_player(),
                data={
                    'bid_data': bid_data,
                    'game_state': self._get_game_state(),
                }
            )
            
            if self.on_decision_needed:
                self.on_decision_needed(context)
    
    def _on_dice_changed(self, dice_data: Dict[str, Any]):
        """Track turn changes via dice rolls."""
        player_id = dice_data.get('player_id')
        if player_id is not None:
            self.current_player_turn = player_id
    
    def _get_current_player(self) -> int:
        """Get the current player's ID."""
        # Try from context first
        if hasattr(self.contexte, 'state') and self.contexte.state:
            return self.contexte.state.get('current_player', 0)
        
        # Fall back to tracked turn
        return self.current_player_turn or 0
    
    def _get_game_state(self) -> Dict[str, Any]:
        """Get current game state from context."""
        if hasattr(self.contexte, 'state'):
            return self.contexte.state.copy()
        return {}
    
    def _extract_property_from_message(self, message: str) -> Optional[str]:
        """Extract property name from buy message."""
        # This would need more sophisticated parsing based on actual messages
        # For now, return None and let the AI figure it out from context
        return None
    
    def _extract_bid_from_message(self, message: str) -> Optional[int]:
        """Extract current bid amount from auction message."""
        # Look for numbers in the message
        import re
        numbers = re.findall(r'\d+', message)
        if numbers:
            # Assume the largest number is the bid amount
            return max(int(n) for n in numbers)
        return None
    
    def _start_context_monitor(self):
        """Start monitoring context for state changes."""
        def monitor():
            last_event_count = 0
            while True:
                try:
                    if hasattr(self.contexte, 'event_history'):
                        current_count = len(self.contexte.event_history)
                        if current_count > last_event_count:
                            # New events detected
                            new_events = self.contexte.event_history[last_event_count:]
                            for event in new_events:
                                self._process_context_event(event)
                            last_event_count = current_count
                except Exception as e:
                    print(f"Error in context monitor: {e}")
                
                time.sleep(0.5)  # Check twice per second
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _process_context_event(self, event: Dict[str, Any]):
        """Process events from context history."""
        event_type = event.get('type')
        
        # Map context events to decision types
        context_to_decision = {
            'property_offer': DecisionType.BUY_PROPERTY,
            'jail_enter': DecisionType.JAIL_STRATEGY,
            'trade_offer': DecisionType.TRADE_RESPONSE,
        }
        
        decision_type = context_to_decision.get(event_type)
        if decision_type:
            context = DecisionContext(
                decision_type=decision_type,
                player_id=event.get('player', self._get_current_player()),
                data={
                    'event': event,
                    'game_state': self._get_game_state(),
                }
            )
            
            if self.on_decision_needed:
                self.on_decision_needed(context)
    
    def get_current_decision_context(self) -> Optional[DecisionContext]:
        """Get the current pending decision if any."""
        return self.pending_decision
    
    def clear_pending_decision(self):
        """Clear the pending decision after it's been handled."""
        self.pending_decision = None