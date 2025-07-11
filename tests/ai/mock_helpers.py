"""
Mock helpers and fixtures for AI system testing.
"""

from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List
import random


class MockMonopolyGame:
    """Mock MonopolyGame for testing."""
    
    def __init__(self, num_players: int = 4):
        self.listeners = MockEventListeners()
        self.contexte = MockContexte(num_players)
        self.num_players = num_players


class MockEventListeners:
    """Mock event listeners system."""
    
    def __init__(self):
        self.callbacks = {}
    
    def on(self, event: str, callback):
        """Register event callback."""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
    
    def emit(self, event: str, data: Any):
        """Emit event to callbacks."""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                callback(data)
    
    def off(self, event: str, callback):
        """Remove event callback."""
        if event in self.callbacks and callback in self.callbacks[event]:
            self.callbacks[event].remove(callback)


class MockContexte:
    """Mock game context."""
    
    def __init__(self, num_players: int = 4):
        self.state = self._create_initial_state(num_players)
        self.event_history = []
    
    def _create_initial_state(self, num_players: int) -> Dict[str, Any]:
        """Create initial game state."""
        state = {
            'current_player': 0,
            'num_players': num_players,
            'player_names': {},
            'player_positions': {},
            'player_money': {},
            'player_in_jail': {},
            'properties': {}
        }
        
        for i in range(num_players):
            state['player_names'][str(i)] = f'Player {i}'
            state['player_positions'][str(i)] = 0
            state['player_money'][str(i)] = 1500
            state['player_in_jail'][str(i)] = False
        
        return state
    
    def add_event(self, event_type: str, data: Dict[str, Any]):
        """Add event to history."""
        self.event_history.append({
            'type': event_type,
            'data': data,
            'player': data.get('player', self.state.get('current_player', 0))
        })


class MockOmniParserResponse:
    """Mock OmniParser API response."""
    
    @staticmethod
    def create_response(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create mock OmniParser response."""
        return {
            'elements': elements,
            'status': 'success',
            'processing_time': 0.5
        }
    
    @staticmethod
    def create_button_element(label: str, x: int, y: int, 
                            width: int = 100, height: int = 40) -> Dict[str, Any]:
        """Create mock button element."""
        return {
            'label': label,
            'confidence': 0.9 + random.random() * 0.09,
            'bbox': [x, y, x + width, y + height],
            'type': 'button'
        }


class MockOpenAIAgent:
    """Mock OpenAI agent for testing."""
    
    def __init__(self, player_id: int, strategy: str = 'balanced'):
        self.player_id = player_id
        self.strategy = strategy
        self.decisions = []
    
    def make_decision(self, game, decision_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make mock decision based on strategy."""
        decision = self._generate_decision(decision_type, context)
        self.decisions.append({
            'type': decision_type,
            'context': context,
            'decision': decision
        })
        return decision
    
    def _generate_decision(self, decision_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate decision based on type and strategy."""
        if decision_type == 'buy_property':
            if self.strategy == 'aggressive':
                return {'buy': True, 'reason': 'Aggressive strategy - buy everything'}
            elif self.strategy == 'conservative':
                return {'buy': False, 'reason': 'Conservative - saving money'}
            else:
                # Balanced - buy if good value
                return {'buy': context.get('price', 0) < 300, 'reason': 'Balanced decision'}
        
        elif decision_type == 'jail_strategy':
            if context.get('has_card'):
                return {'strategy': 'use_card', 'reason': 'Have get out of jail card'}
            elif context.get('turns_in_jail', 0) >= 2:
                return {'strategy': 'pay_fine', 'reason': 'Been in jail too long'}
            else:
                return {'strategy': 'roll', 'reason': 'Try for doubles'}
        
        elif decision_type == 'auction_bid':
            current_bid = context.get('current_bid', 0)
            if self.strategy == 'aggressive':
                return {'bid': current_bid + 50, 'reason': 'Outbid competition'}
            else:
                return {'bid': 0, 'reason': 'Pass on auction'}
        
        elif decision_type == 'build_houses':
            if self.strategy in ['aggressive', 'balanced']:
                return {
                    'builds': [{'property': 'Park Place', 'count': 1}],
                    'reason': 'Building to increase rent'
                }
            else:
                return {'builds': [], 'reason': 'Conserving cash'}
        
        else:
            return {'action': 'default', 'reason': 'Default action'}


def create_test_game_state(scenario: str = 'default') -> Dict[str, Any]:
    """Create test game state for different scenarios."""
    base_state = {
        'current_player': 0,
        'num_players': 4,
        'player_names': {
            '0': 'AI Bot',
            '1': 'Human 1',
            '2': 'Human 2', 
            '3': 'Human 3'
        },
        'player_positions': {'0': 0, '1': 0, '2': 0, '3': 0},
        'player_money': {'0': 1500, '1': 1500, '2': 1500, '3': 1500},
        'player_in_jail': {'0': False, '1': False, '2': False, '3': False},
        'properties': {}
    }
    
    if scenario == 'property_purchase':
        base_state['player_positions']['0'] = 1  # Mediterranean Ave
        
    elif scenario == 'jail':
        base_state['player_in_jail']['0'] = True
        base_state['player_positions']['0'] = 10  # Jail
        
    elif scenario == 'auction':
        base_state['auction_active'] = True
        base_state['auction_property'] = 'Boardwalk'
        base_state['current_bid'] = 200
        
    elif scenario == 'late_game':
        # Late game with properties owned
        base_state['player_money'] = {'0': 800, '1': 200, '2': 3000, '3': 500}
        base_state['properties'] = {
            '1': {'owner': 0, 'name': 'Mediterranean', 'houses': 0},
            '3': {'owner': 0, 'name': 'Baltic', 'houses': 0},
            '6': {'owner': 2, 'name': 'Oriental', 'houses': 2},
            '8': {'owner': 2, 'name': 'Vermont', 'houses': 2},
            '9': {'owner': 2, 'name': 'Connecticut', 'houses': 2}
        }
    
    return base_state


def simulate_game_events(event_listener, events: List[Dict[str, Any]]):
    """Simulate a sequence of game events."""
    for event in events:
        event_type = event['type']
        data = event['data']
        
        if event_type == 'message':
            event_listener._on_message_added(data)
        elif event_type == 'auction_start':
            event_listener._on_auction_started(data)
        elif event_type == 'auction_end':
            event_listener._on_auction_ended(data)
        elif event_type == 'dice':
            event_listener._on_dice_changed(data)