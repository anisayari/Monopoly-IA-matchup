"""
Unit tests for GameEventListener - Test event detection and decision context creation.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai.game_event_listener import GameEventListener, DecisionContext, DecisionType


class TestGameEventListener(unittest.TestCase):
    """Test GameEventListener functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock monopoly game
        self.mock_game = Mock()
        self.mock_game.listeners = Mock()
        self.mock_game.contexte = Mock()
        self.mock_game.contexte.state = {
            'current_player': 0,
            'num_players': 4,
            'player_names': {'0': 'Player 0', '1': 'Player 1'},
            'player_positions': {'0': 5, '1': 10},
            'player_money': {'0': 1500, '1': 1200}
        }
        
        # Create listener
        self.listener = GameEventListener(self.mock_game)
        
        # Track decision callbacks
        self.decision_received = None
        self.listener.on_decision_needed = self._on_decision_callback
    
    def _on_decision_callback(self, context: DecisionContext):
        """Callback to capture decision context."""
        self.decision_received = context
    
    def test_initialization(self):
        """Test listener initialization."""
        # Check that listener is properly initialized
        self.assertIsNotNone(self.listener)
        self.assertEqual(self.listener.game, self.mock_game)
        self.assertIsNone(self.listener.pending_decision)
        self.assertFalse(self.listener.auction_active)
    
    def test_buy_property_detection(self):
        """Test detection of buy property decisions."""
        # Simulate buy property message
        message_data = {
            'message': 'Do you want to buy Park Place for $350?',
            'group': 'property_offer',
            'player': 0
        }
        
        self.listener._on_message_added(message_data)
        
        # Check decision was detected
        self.assertIsNotNone(self.decision_received)
        self.assertEqual(self.decision_received.decision_type, DecisionType.BUY_PROPERTY)
        self.assertEqual(self.decision_received.player_id, 0)
        self.assertEqual(self.decision_received.message, message_data['message'])
    
    def test_jail_decision_detection(self):
        """Test detection of jail decisions."""
        test_cases = [
            ('Pay the bail to get out of jail?', DecisionType.JAIL_STRATEGY),
            ('Use jail free card?', DecisionType.JAIL_STRATEGY),
            ('Pay jail fine prompt', DecisionType.JAIL_STRATEGY)
        ]
        
        for message, expected_type in test_cases:
            self.decision_received = None
            message_data = {
                'message': message,
                'group': 'jail_options',
                'player': 1
            }
            
            self.listener._on_message_added(message_data)
            
            self.assertIsNotNone(self.decision_received, f"Failed for message: {message}")
            self.assertEqual(self.decision_received.decision_type, expected_type)
            self.assertEqual(self.decision_received.player_id, 0)  # Uses current player
    
    def test_auction_detection(self):
        """Test auction event detection."""
        # Test auction started
        auction_data = {
            'property': 'Boardwalk',
            'starting_bid': 100
        }
        
        self.listener._on_auction_started(auction_data)
        
        self.assertTrue(self.listener.auction_active)
        self.assertIsNotNone(self.decision_received)
        self.assertEqual(self.decision_received.decision_type, DecisionType.AUCTION_BID)
        
        # Test auction ended
        self.listener._on_auction_ended({})
        self.assertFalse(self.listener.auction_active)
    
    def test_decision_patterns(self):
        """Test various decision pattern detections."""
        pattern_tests = [
            ('What would you like to do?', DecisionType.GENERAL_ACTION),
            ('Roll again for doubles!', DecisionType.ROLL_DICE),
            ('Would you like to mortgage a property?', DecisionType.MORTGAGE_PROPERTY),
            ('Do you want to trade?', DecisionType.TRADE_OFFER),
            ('Build a house on which property?', DecisionType.BUILD_HOUSES),
            ('Current bid is $200, enter your bid:', DecisionType.AUCTION_BID)
        ]
        
        for message, expected_type in pattern_tests:
            self.decision_received = None
            message_data = {'message': message, 'group': '', 'player': 0}
            
            self.listener._on_message_added(message_data)
            
            if expected_type:
                self.assertIsNotNone(self.decision_received, f"Failed to detect: {message}")
                self.assertEqual(self.decision_received.decision_type, expected_type)
    
    def test_context_building(self):
        """Test decision context building."""
        message_data = {
            'message': 'Do you want to buy Mediterranean Avenue?',
            'group': 'property_offer',
            'player': 0,
            'extra_data': {'price': 60}
        }
        
        self.listener._on_message_added(message_data)
        
        context = self.decision_received
        self.assertIsNotNone(context)
        self.assertEqual(context.player_id, 0)
        self.assertTrue(context.requires_immediate_response)
        self.assertIn('message_data', context.data)
        self.assertIn('game_state', context.data)
        self.assertEqual(context.data['message_data'], message_data)
    
    def test_get_current_player(self):
        """Test current player detection."""
        # Test from context
        player_id = self.listener._get_current_player()
        self.assertEqual(player_id, 0)
        
        # Test from tracked turn
        self.listener.current_player_turn = 2
        self.mock_game.contexte.state = {}
        player_id = self.listener._get_current_player()
        self.assertEqual(player_id, 2)
    
    def test_dice_changed_tracking(self):
        """Test turn tracking via dice changes."""
        dice_data = {'player_id': 3, 'dice1': 4, 'dice2': 2}
        self.listener._on_dice_changed(dice_data)
        
        self.assertEqual(self.listener.current_player_turn, 3)
    
    def test_no_decision_for_irrelevant_messages(self):
        """Test that irrelevant messages don't trigger decisions."""
        irrelevant_messages = [
            'Player 1 rolled a 7',
            'You landed on Free Parking',
            'Collect $200 salary as you pass GO',
            'You drew a Chance card'
        ]
        
        for message in irrelevant_messages:
            self.decision_received = None
            message_data = {'message': message, 'group': '', 'player': 0}
            
            self.listener._on_message_added(message_data)
            
            self.assertIsNone(self.decision_received, 
                            f"Incorrectly triggered decision for: {message}")
    
    def test_extract_bid_from_message(self):
        """Test bid amount extraction."""
        test_cases = [
            ('Current bid is $500', 500),
            ('The bid is now 1200', 1200),
            ('Bid: $50', 50),
            ('No numbers here', None)
        ]
        
        for message, expected in test_cases:
            result = self.listener._extract_bid_from_message(message)
            self.assertEqual(result, expected, f"Failed for: {message}")
    
    def test_event_listener_setup(self):
        """Test that all event listeners are properly set up."""
        # Check that listeners were registered
        expected_events = [
            'message_added',
            'auction_started', 
            'auction_ended',
            'auction_bid',
            'player_dice_changed'
        ]
        
        for event in expected_events:
            self.mock_game.listeners.on.assert_any_call(event, unittest.mock.ANY)


class TestDecisionContext(unittest.TestCase):
    """Test DecisionContext dataclass."""
    
    def test_decision_context_creation(self):
        """Test creating decision context."""
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=1,
            data={'property': 'Park Place'},
            message='Buy Park Place?'
        )
        
        self.assertEqual(context.decision_type, DecisionType.BUY_PROPERTY)
        self.assertEqual(context.player_id, 1)
        self.assertEqual(context.data['property'], 'Park Place')
        self.assertEqual(context.message, 'Buy Park Place?')
        self.assertTrue(context.requires_immediate_response)
        self.assertIsNotNone(context.timestamp)
    
    def test_decision_type_enum(self):
        """Test DecisionType enum values."""
        expected_types = [
            'buy_property',
            'jail_strategy',
            'build_houses',
            'mortgage_property',
            'trade_offer',
            'trade_response',
            'auction_bid',
            'general_action',
            'roll_dice'
        ]
        
        actual_types = [dt.value for dt in DecisionType]
        for expected in expected_types:
            self.assertIn(expected, actual_types)


if __name__ == '__main__':
    unittest.main()