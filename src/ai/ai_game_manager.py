"""
AIGameManager - Central orchestrator between real game and AI.

This module manages the synchronization between:
- Real game state (from Dolphin)
- AI simulation state (monopoly_ai)
- Decision making and action execution
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from queue import Queue, Empty
import os
import sys

# Add monopoly_ai to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../monopoly_ai'))

from monopoly_ai.ai.openai_agent import OpenAIMonopolyAgent
from monopoly_ai.ai.game_manager import MonopolyGameManager
from monopoly_ai.game.monopoly import MonopolyGame
from monopoly_ai.game.player import Player

from .game_event_listener import GameEventListener, DecisionContext, DecisionType
from .action_executor import ActionExecutor


@dataclass
class AIPlayer:
    """Represents an AI-controlled player."""
    player_id: int
    name: str
    agent: OpenAIMonopolyAgent
    is_active: bool = True


class AIGameManager:
    """
    Central manager that orchestrates AI decisions for the real game.
    
    Maintains synchronization between real and simulated game states.
    """
    
    def __init__(self, monopoly_game, ai_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI Game Manager.
        
        Args:
            monopoly_game: The real game instance
            ai_config: Configuration for AI players
        """
        self.real_game = monopoly_game
        self.ai_config = ai_config or {}
        
        # Components
        self.event_listener = GameEventListener(monopoly_game)
        self.action_executor = ActionExecutor()
        
        # AI simulation
        self.sim_game = None  # Will be initialized when game starts
        self.game_manager = None  # MonopolyGameManager instance
        self.ai_players: Dict[int, AIPlayer] = {}
        
        # State synchronization
        self.last_sync_time = 0
        self.sync_interval = 1.0  # Sync every second
        
        # Decision queue
        self.decision_queue = Queue()
        self.decision_thread = None
        self.running = False
        
        # Setup
        self._setup()
    
    def _setup(self):
        """Setup the AI manager."""
        # Connect event listener
        self.event_listener.on_decision_needed = self._on_decision_needed
        
        # Initialize AI players based on config
        self._initialize_ai_players()
        
        # Start decision processing thread
        self._start_decision_processor()
    
    def _initialize_ai_players(self):
        """Initialize AI players based on configuration."""
        # Default: Make player 0 AI-controlled
        ai_player_ids = self.ai_config.get('ai_players', [0])
        
        for player_id in ai_player_ids:
            # Create OpenAI agent for this player
            agent = OpenAIMonopolyAgent(
                player_id=player_id,
                api_key=self.ai_config.get('openai_api_key', os.getenv('OPENAI_API_KEY')),
                model=self.ai_config.get('model', 'gpt-4-turbo-preview'),
                temperature=self.ai_config.get('temperature', 0.7)
            )
            
            self.ai_players[player_id] = AIPlayer(
                player_id=player_id,
                name=f"AI Player {player_id}",
                agent=agent
            )
    
    def _on_decision_needed(self, context: DecisionContext):
        """Handle when a decision is needed from the AI."""
        # Check if this decision is for an AI player
        if context.player_id in self.ai_players:
            print(f"[AI Manager] Decision needed for player {context.player_id}: {context.decision_type.value}")
            self.decision_queue.put(context)
    
    def _start_decision_processor(self):
        """Start the thread that processes AI decisions."""
        self.running = True
        self.decision_thread = threading.Thread(target=self._process_decisions, daemon=True)
        self.decision_thread.start()
    
    def _process_decisions(self):
        """Process decisions from the queue."""
        while self.running:
            try:
                # Get decision with timeout
                context = self.decision_queue.get(timeout=0.5)
                
                # Sync game state if needed
                self._sync_game_state()
                
                # Make AI decision
                decision = self._make_ai_decision(context)
                
                if decision:
                    # Execute the action
                    self._execute_decision(decision, context)
                
            except Empty:
                # No decisions pending
                continue
            except Exception as e:
                print(f"[AI Manager] Error processing decision: {e}")
                import traceback
                traceback.print_exc()
    
    def _sync_game_state(self):
        """Synchronize the simulated game with the real game state."""
        current_time = time.time()
        
        # Only sync if enough time has passed
        if current_time - self.last_sync_time < self.sync_interval:
            return
        
        try:
            # Get real game state from context
            real_state = self.real_game.contexte.state if hasattr(self.real_game.contexte, 'state') else {}
            
            if not real_state:
                return
            
            # Initialize simulation if needed
            if self.sim_game is None:
                self._initialize_simulation(real_state)
            
            # Update simulation state
            self._update_simulation_state(real_state)
            
            self.last_sync_time = current_time
            
        except Exception as e:
            print(f"[AI Manager] Error syncing game state: {e}")
    
    def _initialize_simulation(self, real_state: Dict[str, Any]):
        """Initialize the AI simulation game."""
        # Create players based on real game
        players = []
        for i in range(real_state.get('num_players', 2)):
            player_name = real_state.get('player_names', {}).get(str(i), f"Player {i}")
            player = Player(i, player_name)
            players.append(player)
        
        # Initialize simulation game
        self.sim_game = MonopolyGame(players)
        
        # Initialize game manager with AI agents
        self.game_manager = MonopolyGameManager(self.sim_game)
        
        # Register AI agents
        for player_id, ai_player in self.ai_players.items():
            if player_id < len(players):
                self.game_manager.set_agent(player_id, ai_player.agent)
    
    def _update_simulation_state(self, real_state: Dict[str, Any]):
        """Update simulation to match real game state."""
        if not self.sim_game:
            return
        
        # Update player states
        for i, player in enumerate(self.sim_game.players):
            player_key = str(i)
            
            # Update position
            if 'player_positions' in real_state:
                player.position = real_state['player_positions'].get(player_key, 0)
            
            # Update money
            if 'player_money' in real_state:
                player.money = real_state['player_money'].get(player_key, 1500)
            
            # Update jail status
            if 'player_in_jail' in real_state:
                player.in_jail = real_state['player_in_jail'].get(player_key, False)
            
            # Update properties
            if 'properties' in real_state:
                player.properties.clear()
                for prop_id, prop_data in real_state['properties'].items():
                    if prop_data.get('owner') == i:
                        # Add property to player
                        property_obj = self.sim_game.board.get_property_by_position(int(prop_id))
                        if property_obj:
                            player.properties.append(property_obj)
                            property_obj.owner = player
        
        # Update current player turn
        if 'current_player' in real_state:
            self.sim_game.current_player_index = real_state['current_player']
    
    def _make_ai_decision(self, context: DecisionContext) -> Optional[Dict[str, Any]]:
        """Make an AI decision based on the context."""
        if not self.game_manager or context.player_id not in self.ai_players:
            return None
        
        ai_player = self.ai_players[context.player_id]
        
        try:
            # Map decision type to AI method
            if context.decision_type == DecisionType.BUY_PROPERTY:
                return self._decide_buy_property(ai_player, context)
            
            elif context.decision_type == DecisionType.JAIL_STRATEGY:
                return self._decide_jail_strategy(ai_player, context)
            
            elif context.decision_type == DecisionType.BUILD_HOUSES:
                return self._decide_build_houses(ai_player, context)
            
            elif context.decision_type == DecisionType.AUCTION_BID:
                return self._decide_auction_bid(ai_player, context)
            
            elif context.decision_type == DecisionType.TRADE_OFFER:
                return self._decide_trade_offer(ai_player, context)
            
            elif context.decision_type == DecisionType.TRADE_RESPONSE:
                return self._decide_trade_response(ai_player, context)
            
            elif context.decision_type == DecisionType.MORTGAGE_PROPERTY:
                return self._decide_mortgage(ai_player, context)
            
            elif context.decision_type == DecisionType.GENERAL_ACTION:
                return self._decide_general_action(ai_player, context)
            
            elif context.decision_type == DecisionType.ROLL_DICE:
                return {'action': 'roll_dice'}
            
        except Exception as e:
            print(f"[AI Manager] Error making decision: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _decide_buy_property(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide whether to buy a property."""
        # Get current property from context
        game_state = context.data.get('game_state', {})
        player_position = game_state.get('player_positions', {}).get(str(ai_player.player_id), 0)
        
        # Get property at current position
        property_obj = self.sim_game.board.get_property_by_position(player_position) if self.sim_game else None
        
        if property_obj:
            # Ask AI agent
            decision = ai_player.agent.make_decision(
                self.sim_game,
                'buy_property',
                {'property': property_obj}
            )
            
            return {
                'action': 'buy' if decision.get('buy', False) else 'pass',
                'property': property_obj.name,
                'reason': decision.get('reason', '')
            }
        
        return {'action': 'pass'}
    
    def _decide_jail_strategy(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide jail strategy."""
        player = self.sim_game.players[ai_player.player_id] if self.sim_game else None
        
        if player:
            decision = ai_player.agent.make_decision(
                self.sim_game,
                'jail_strategy',
                {
                    'turns_in_jail': getattr(player, 'jail_turns', 0),
                    'has_card': getattr(player, 'get_out_of_jail_cards', 0) > 0
                }
            )
            
            strategy = decision.get('strategy', 'roll')
            return {
                'action': strategy,  # 'use_card', 'pay_fine', or 'roll'
                'reason': decision.get('reason', '')
            }
        
        return {'action': 'roll'}
    
    def _decide_build_houses(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide whether to build houses."""
        player = self.sim_game.players[ai_player.player_id] if self.sim_game else None
        
        if player:
            # Get buildable properties
            monopolies = self._get_player_monopolies(player)
            
            if monopolies:
                decision = ai_player.agent.make_decision(
                    self.sim_game,
                    'build_houses',
                    {'monopolies': monopolies}
                )
                
                builds = decision.get('builds', [])
                if builds:
                    return {
                        'action': 'build',
                        'builds': builds,
                        'reason': decision.get('reason', '')
                    }
        
        return {'action': 'skip'}
    
    def _decide_auction_bid(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide auction bid amount."""
        current_bid = context.data.get('current_bid', 0)
        
        decision = ai_player.agent.make_decision(
            self.sim_game,
            'auction_bid',
            {
                'current_bid': current_bid,
                'property': context.data.get('auction_property')
            }
        )
        
        bid_amount = decision.get('bid', 0)
        
        return {
            'action': 'bid' if bid_amount > current_bid else 'pass',
            'amount': bid_amount,
            'reason': decision.get('reason', '')
        }
    
    def _decide_trade_offer(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide on trade offer to make."""
        # This is complex - for now, skip trades
        return {'action': 'skip'}
    
    def _decide_trade_response(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide on response to trade offer."""
        # This is complex - for now, decline trades
        return {'action': 'decline'}
    
    def _decide_mortgage(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide which properties to mortgage/unmortgage."""
        player = self.sim_game.players[ai_player.player_id] if self.sim_game else None
        
        if player and player.money < 0:
            # Need to raise money
            decision = ai_player.agent.make_decision(
                self.sim_game,
                'mortgage_decision',
                {'debt': abs(player.money)}
            )
            
            properties_to_mortgage = decision.get('mortgage', [])
            if properties_to_mortgage:
                return {
                    'action': 'mortgage',
                    'properties': properties_to_mortgage,
                    'reason': decision.get('reason', '')
                }
        
        return {'action': 'skip'}
    
    def _decide_general_action(self, ai_player: AIPlayer, context: DecisionContext) -> Dict[str, Any]:
        """Decide on general action (manage properties, trade, etc)."""
        # For now, just end turn
        return {'action': 'end_turn'}
    
    def _execute_decision(self, decision: Dict[str, Any], context: DecisionContext):
        """Execute the AI's decision in the real game."""
        action = decision.get('action')
        
        print(f"[AI Manager] Executing action: {action}")
        if decision.get('reason'):
            print(f"[AI Manager] Reason: {decision['reason']}")
        
        # Use ActionExecutor to perform the action
        success = self.action_executor.execute_action(action, decision, context)
        
        if not success:
            print(f"[AI Manager] Failed to execute action: {action}")
    
    def _get_player_monopolies(self, player) -> List[str]:
        """Get list of monopolies owned by player."""
        monopolies = []
        
        # Group properties by color
        color_groups = {}
        for prop in player.properties:
            if hasattr(prop, 'color'):
                if prop.color not in color_groups:
                    color_groups[prop.color] = []
                color_groups[prop.color].append(prop)
        
        # Check for complete monopolies
        for color, props in color_groups.items():
            # This would need the actual monopoly checking logic
            # For now, simplified
            if len(props) >= 2:  # Simplified check
                monopolies.append(color)
        
        return monopolies
    
    def start(self):
        """Start the AI manager."""
        print("[AI Manager] Starting AI Game Manager...")
        self.running = True
    
    def stop(self):
        """Stop the AI manager."""
        print("[AI Manager] Stopping AI Game Manager...")
        self.running = False
        if self.decision_thread:
            self.decision_thread.join(timeout=2.0)
    
    def set_ai_player(self, player_id: int, enabled: bool = True):
        """Enable or disable AI control for a player."""
        if enabled and player_id not in self.ai_players:
            # Add new AI player
            agent = OpenAIMonopolyAgent(
                player_id=player_id,
                api_key=self.ai_config.get('openai_api_key', os.getenv('OPENAI_API_KEY')),
                model=self.ai_config.get('model', 'gpt-4-turbo-preview')
            )
            
            self.ai_players[player_id] = AIPlayer(
                player_id=player_id,
                name=f"AI Player {player_id}",
                agent=agent
            )
        elif not enabled and player_id in self.ai_players:
            # Remove AI player
            del self.ai_players[player_id]