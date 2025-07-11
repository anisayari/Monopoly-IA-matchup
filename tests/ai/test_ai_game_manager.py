"""
Unit tests for AIGameManager - Test AI orchestration and decision making.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from queue import Queue
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai.ai_game_manager import AIGameManager, AIPlayer
from src.ai.game_event_listener import DecisionContext, DecisionType


class TestAIGameManager(unittest.TestCase):
    """Test AIGameManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock monopoly game
        self.mock_game = Mock()
        self.mock_game.listeners = Mock()
        self.mock_game.contexte = Mock()
        self.mock_game.contexte.state = {
            'current_player': 0,
            'num_players': 2,
            'player_names': {'0': 'AI Player', '1': 'Human Player'},
            'player_positions': {'0': 0, '1': 0},
            'player_money': {'0': 1500, '1': 1500},
            'properties': {}
        }
        
        # AI config
        self.ai_config = {
            'ai_players': [0],
            'openai_api_key': 'test-key',
            'model': 'gpt-4',
            'temperature': 0.7
        }
        
        # Create AI manager with mocked components
        with patch('src.ai.ai_game_manager.GameEventListener'):
            with patch('src.ai.ai_game_manager.ActionExecutor'):
                self.ai_manager = AIGameManager(self.mock_game, self.ai_config)
    
    def test_initialization(self):
        """Test AI manager initialization."""
        self.assertIsNotNone(self.ai_manager)
        self.assertEqual(len(self.ai_manager.ai_players), 1)
        self.assertIn(0, self.ai_manager.ai_players)
        self.assertTrue(self.ai_manager.running)
    
    def test_ai_player_creation(self):
        """Test AI player creation."""
        ai_player = self.ai_manager.ai_players[0]
        self.assertIsInstance(ai_player, AIPlayer)
        self.assertEqual(ai_player.player_id, 0)
        self.assertEqual(ai_player.name, "AI Player 0")
        self.assertTrue(ai_player.is_active)
    
    def test_decision_queue_processing(self):
        """Test decision queue handling."""
        # Create test decision
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0,
            data={'property': 'Boardwalk'}
        )
        
        # Add to queue
        self.ai_manager.decision_queue.put(context)
        
        # Check queue has item
        self.assertEqual(self.ai_manager.decision_queue.qsize(), 1)
        
        # Process would happen in thread
        item = self.ai_manager.decision_queue.get_nowait()
        self.assertEqual(item, context)
    
    def test_on_decision_needed(self):
        """Test decision needed callback."""
        # Test AI player decision
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0
        )
        
        self.ai_manager._on_decision_needed(context)
        self.assertEqual(self.ai_manager.decision_queue.qsize(), 1)
        
        # Test non-AI player (should not queue)
        self.ai_manager.decision_queue = Queue()
        context.player_id = 1
        self.ai_manager._on_decision_needed(context)
        self.assertEqual(self.ai_manager.decision_queue.qsize(), 0)
    
    @patch('src.ai.ai_game_manager.MonopolyGame')
    def test_simulation_initialization(self, mock_monopoly_game):
        """Test game simulation initialization."""
        # Trigger sync to initialize simulation
        self.ai_manager.last_sync_time = 0
        self.ai_manager._sync_game_state()
        
        # Check simulation was created
        self.assertIsNotNone(self.ai_manager.sim_game)
        self.assertIsNotNone(self.ai_manager.game_manager)
    
    def test_state_synchronization(self):
        """Test state sync between real and simulated game."""
        # Initialize simulation first
        self.ai_manager._initialize_simulation(self.mock_game.contexte.state)
        
        # Update real game state
        new_state = {
            'current_player': 1,
            'num_players': 2,
            'player_positions': {'0': 5, '1': 10},
            'player_money': {'0': 1200, '1': 1800},
            'properties': {
                '1': {'owner': 0, 'name': 'Mediterranean'},
                '3': {'owner': 1, 'name': 'Baltic'}
            }
        }
        
        self.mock_game.contexte.state = new_state
        
        # Sync state
        self.ai_manager._update_simulation_state(new_state)
        
        # Verify sync
        self.assertEqual(self.ai_manager.sim_game.current_player_index, 1)
        self.assertEqual(self.ai_manager.sim_game.players[0].position, 5)
        self.assertEqual(self.ai_manager.sim_game.players[0].money, 1200)
    
    def test_buy_property_decision(self):
        """Test buy property decision making."""
        # Mock AI agent
        mock_agent = Mock()
        mock_agent.make_decision.return_value = {
            'buy': True,
            'reason': 'Good investment'
        }
        
        ai_player = AIPlayer(0, "Test AI", mock_agent)
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0,
            data={'game_state': {'player_positions': {'0': 1}}}
        )
        
        # Initialize simulation
        self.ai_manager._initialize_simulation(self.mock_game.contexte.state)
        
        # Make decision
        decision = self.ai_manager._decide_buy_property(ai_player, context)
        
        self.assertEqual(decision['action'], 'buy')
        self.assertEqual(decision['reason'], 'Good investment')
        mock_agent.make_decision.assert_called_once()
    
    def test_jail_strategy_decision(self):
        """Test jail strategy decision."""
        mock_agent = Mock()
        mock_agent.make_decision.return_value = {
            'strategy': 'pay_fine',
            'reason': 'Need to get out quickly'
        }
        
        ai_player = AIPlayer(0, "Test AI", mock_agent)
        context = DecisionContext(
            decision_type=DecisionType.JAIL_STRATEGY,
            player_id=0
        )
        
        self.ai_manager._initialize_simulation(self.mock_game.contexte.state)
        
        decision = self.ai_manager._decide_jail_strategy(ai_player, context)
        
        self.assertEqual(decision['action'], 'pay_fine')
        self.assertIn('reason', decision)
    
    def test_auction_bid_decision(self):
        """Test auction bidding decision."""
        mock_agent = Mock()
        mock_agent.make_decision.return_value = {
            'bid': 250,
            'reason': 'Worth up to $300'
        }
        
        ai_player = AIPlayer(0, "Test AI", mock_agent)
        context = DecisionContext(
            decision_type=DecisionType.AUCTION_BID,
            player_id=0,
            data={'current_bid': 200}
        )
        
        self.ai_manager._initialize_simulation(self.mock_game.contexte.state)
        
        decision = self.ai_manager._decide_auction_bid(ai_player, context)
        
        self.assertEqual(decision['action'], 'bid')
        self.assertEqual(decision['amount'], 250)
    
    def test_decision_execution(self):
        """Test decision execution."""
        decision = {
            'action': 'buy',
            'reason': 'Strategic location'
        }
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0
        )
        
        # Mock action executor
        self.ai_manager.action_executor.execute_action = Mock(return_value=True)
        
        # Execute decision
        self.ai_manager._execute_decision(decision, context)
        
        # Verify execution
        self.ai_manager.action_executor.execute_action.assert_called_once_with(
            'buy', decision, context
        )
    
    def test_set_ai_player(self):
        """Test enabling/disabling AI for players."""
        # Enable AI for player 2
        self.ai_manager.set_ai_player(2, enabled=True)
        self.assertIn(2, self.ai_manager.ai_players)
        
        # Disable AI for player 0
        self.ai_manager.set_ai_player(0, enabled=False)
        self.assertNotIn(0, self.ai_manager.ai_players)
        
        # Re-enable
        self.ai_manager.set_ai_player(0, enabled=True)
        self.assertIn(0, self.ai_manager.ai_players)
    
    def test_stop_manager(self):
        """Test stopping AI manager."""
        self.assertTrue(self.ai_manager.running)
        
        self.ai_manager.stop()
        
        self.assertFalse(self.ai_manager.running)
    
    def test_error_handling_in_decisions(self):
        """Test error handling during decision making."""
        # Create context with missing data
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0,
            data={}  # Missing expected data
        )
        
        # Should not crash
        decision = self.ai_manager._make_ai_decision(context)
        
        # Should return None or safe default
        self.assertTrue(decision is None or 'action' in decision)


class TestAIPlayer(unittest.TestCase):
    """Test AIPlayer dataclass."""
    
    def test_ai_player_creation(self):
        """Test creating AI player."""
        mock_agent = Mock()
        player = AIPlayer(
            player_id=1,
            name="Test AI",
            agent=mock_agent
        )
        
        self.assertEqual(player.player_id, 1)
        self.assertEqual(player.name, "Test AI")
        self.assertEqual(player.agent, mock_agent)
        self.assertTrue(player.is_active)


if __name__ == '__main__':
    unittest.main()