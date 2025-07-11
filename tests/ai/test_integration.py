"""
Integration tests for the AI system - Test complete workflow end-to-end.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os
import time
from queue import Queue
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai.game_event_listener import GameEventListener, DecisionContext, DecisionType
from src.ai.ai_game_manager import AIGameManager, AIPlayer
from src.ai.action_executor import ActionExecutor, UIElement
from src.ai.ai_integration import AIIntegration


class TestAISystemIntegration(unittest.TestCase):
    """Test complete AI system integration."""
    
    def setUp(self):
        """Set up integrated test environment."""
        # Create mock game
        self.mock_game = Mock()
        self.mock_game.listeners = Mock()
        self.mock_game.contexte = Mock()
        self.mock_game.contexte.state = {
            'current_player': 0,
            'num_players': 4,
            'player_names': {
                '0': 'AI Bot',
                '1': 'Human 1', 
                '2': 'Human 2',
                '3': 'Human 3'
            },
            'player_positions': {'0': 1, '1': 5, '2': 10, '3': 15},
            'player_money': {'0': 1500, '1': 1500, '2': 1500, '3': 1500},
            'properties': {}
        }
        
        # AI config
        self.ai_config = {
            'ai_players': [0],
            'openai_api_key': 'test-key',
            'model': 'gpt-4',
            'temperature': 0.7
        }
    
    @patch('src.ai.ai_game_manager.OpenAIMonopolyAgent')
    def test_full_decision_flow(self, mock_agent_class):
        """Test complete flow from event to action execution."""
        # Create mock agent
        mock_agent = Mock()
        mock_agent.make_decision.return_value = {
            'buy': True,
            'reason': 'Strategic property'
        }
        mock_agent_class.return_value = mock_agent
        
        # Create AI manager
        with patch('src.ai.ai_game_manager.ActionExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_action.return_value = True
            mock_executor_class.return_value = mock_executor
            
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            # Simulate buy property event
            message_data = {
                'message': 'Do you want to buy Mediterranean Avenue for $60?',
                'group': 'property_offer',
                'player': 0
            }
            
            # Trigger event through listener
            ai_manager.event_listener._on_message_added(message_data)
            
            # Give time for processing
            time.sleep(0.1)
            
            # Verify decision was queued
            self.assertGreater(ai_manager.decision_queue.qsize(), 0)
            
            # Process the decision manually (normally done in thread)
            context = ai_manager.decision_queue.get()
            ai_manager._sync_game_state()
            decision = ai_manager._make_ai_decision(context)
            
            # Verify decision
            self.assertIsNotNone(decision)
            self.assertEqual(decision['action'], 'buy')
            
            # Execute decision
            ai_manager._execute_decision(decision, context)
            
            # Verify execution
            mock_executor.execute_action.assert_called_once_with('buy', decision, context)
    
    def test_multiple_ai_players(self):
        """Test system with multiple AI players."""
        # Configure multiple AI players
        self.ai_config['ai_players'] = [0, 2]
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent'):
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            # Verify both AI players created
            self.assertEqual(len(ai_manager.ai_players), 2)
            self.assertIn(0, ai_manager.ai_players)
            self.assertIn(2, ai_manager.ai_players)
            
            # Test decisions for both players
            for player_id in [0, 2]:
                context = DecisionContext(
                    decision_type=DecisionType.ROLL_DICE,
                    player_id=player_id
                )
                
                ai_manager._on_decision_needed(context)
            
            # Both should be queued
            self.assertEqual(ai_manager.decision_queue.qsize(), 2)
    
    def test_event_to_decision_mapping(self):
        """Test various events map to correct decisions."""
        test_cases = [
            (
                {'message': 'Want to buy Boardwalk?', 'group': 'property_offer'},
                DecisionType.BUY_PROPERTY
            ),
            (
                {'message': 'Pay the bail?', 'group': 'jail_options'},
                DecisionType.JAIL_STRATEGY
            ),
            (
                {'message': 'Current bid is $100', 'group': 'auction'},
                DecisionType.AUCTION_BID
            ),
            (
                {'message': 'Build houses on which property?', 'group': 'build'},
                DecisionType.BUILD_HOUSES
            )
        ]
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent'):
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            for message_data, expected_type in test_cases:
                # Clear queue
                ai_manager.decision_queue = Queue()
                
                # Trigger event
                message_data['player'] = 0
                ai_manager.event_listener._on_message_added(message_data)
                
                # Check decision queued
                if ai_manager.decision_queue.qsize() > 0:
                    context = ai_manager.decision_queue.get()
                    self.assertEqual(context.decision_type, expected_type)
    
    def test_state_synchronization(self):
        """Test game state stays synchronized."""
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent'):
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            # Initial sync
            ai_manager._sync_game_state()
            
            # Update real game state
            self.mock_game.contexte.state['player_money']['0'] = 1200
            self.mock_game.contexte.state['player_positions']['0'] = 5
            self.mock_game.contexte.state['properties']['1'] = {
                'owner': 0,
                'name': 'Mediterranean'
            }
            
            # Force new sync
            ai_manager.last_sync_time = 0
            ai_manager._sync_game_state()
            
            # Verify simulation updated
            if ai_manager.sim_game:
                self.assertEqual(ai_manager.sim_game.players[0].money, 1200)
                self.assertEqual(ai_manager.sim_game.players[0].position, 5)
    
    def test_error_recovery(self):
        """Test system handles errors gracefully."""
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent') as mock_agent_class:
            # Make agent throw error
            mock_agent = Mock()
            mock_agent.make_decision.side_effect = Exception("API Error")
            mock_agent_class.return_value = mock_agent
            
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            # Create decision context
            context = DecisionContext(
                decision_type=DecisionType.BUY_PROPERTY,
                player_id=0
            )
            
            # Should handle error without crashing
            decision = ai_manager._make_ai_decision(context)
            self.assertIsNone(decision)
    
    def test_ai_integration_helper(self):
        """Test AIIntegration helper class."""
        # Test enabling AI
        ai_manager = AIIntegration.enable_ai_for_game(self.mock_game, self.ai_config)
        
        self.assertIsNotNone(ai_manager)
        self.assertTrue(ai_manager.running)
        
        # Test add_ai_to_main
        ai_manager2 = AIIntegration.add_ai_to_main(
            self.mock_game,
            enable_ai=True,
            ai_players=[1, 3]
        )
        
        self.assertIsNotNone(ai_manager2)
        self.assertIn(1, ai_manager2.ai_players)
        self.assertIn(3, ai_manager2.ai_players)
        
        # Clean up
        ai_manager.stop()
        ai_manager2.stop()
    
    @patch('flask.Flask')
    def test_flask_integration(self, mock_flask):
        """Test Flask app integration."""
        # Create mock Flask app
        app = Mock()
        app.route = Mock(return_value=lambda f: f)
        app.get_json = Mock(return_value={'players': [0, 1]})
        
        # Add AI to Flask
        AIIntegration.add_ai_to_flask_app(app, self.mock_game)
        
        # Verify routes added
        expected_routes = [
            '/api/ai/enable',
            '/api/ai/disable', 
            '/api/ai/status',
            '/api/ai/set_player'
        ]
        
        for route in expected_routes:
            app.route.assert_any_call(route, methods=unittest.mock.ANY)
    
    def test_concurrent_decisions(self):
        """Test handling multiple concurrent decisions."""
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent'):
            ai_manager = AIGameManager(self.mock_game, self.ai_config)
            
            # Queue multiple decisions rapidly
            contexts = []
            for i in range(5):
                context = DecisionContext(
                    decision_type=DecisionType.GENERAL_ACTION,
                    player_id=0,
                    data={'action_num': i}
                )
                contexts.append(context)
                ai_manager._on_decision_needed(context)
            
            # Verify all queued
            self.assertEqual(ai_manager.decision_queue.qsize(), 5)
            
            # Process all
            processed = []
            while not ai_manager.decision_queue.empty():
                processed.append(ai_manager.decision_queue.get())
            
            self.assertEqual(len(processed), 5)


class TestEndToEndScenarios(unittest.TestCase):
    """Test complete game scenarios."""
    
    def test_property_purchase_scenario(self):
        """Test complete property purchase scenario."""
        # Setup
        mock_game = Mock()
        mock_game.listeners = Mock()
        mock_game.contexte = Mock()
        mock_game.contexte.state = {
            'current_player': 0,
            'num_players': 2,
            'player_money': {'0': 1500, '1': 1500},
            'player_positions': {'0': 1, '1': 0}
        }
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent.make_decision.return_value = {'buy': True, 'reason': 'Good value'}
            mock_agent_class.return_value = mock_agent
            
            with patch('src.ai.action_executor.ActionExecutor') as mock_executor_class:
                mock_executor = Mock()
                mock_executor.execute_action.return_value = True
                mock_executor_class.return_value = mock_executor
                
                # Create manager
                ai_manager = AIGameManager(mock_game, {'ai_players': [0]})
                
                # Simulate landing on property
                # 1. Game shows property offer
                ai_manager.event_listener._on_message_added({
                    'message': 'Do you want to buy Park Place for $350?',
                    'group': 'property_offer',
                    'player': 0
                })
                
                # 2. AI processes decision
                time.sleep(0.1)
                context = ai_manager.decision_queue.get()
                decision = ai_manager._make_ai_decision(context)
                
                # 3. Execute action
                ai_manager._execute_decision(decision, context)
                
                # Verify flow
                self.assertEqual(decision['action'], 'buy')
                mock_executor.execute_action.assert_called_with('buy', decision, context)
    
    def test_jail_scenario(self):
        """Test complete jail scenario."""
        mock_game = Mock()
        mock_game.listeners = Mock()
        mock_game.contexte = Mock()
        mock_game.contexte.state = {
            'current_player': 0,
            'player_in_jail': {'0': True}
        }
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent.make_decision.return_value = {
                'strategy': 'pay_fine',
                'reason': 'Need to move quickly'
            }
            mock_agent_class.return_value = mock_agent
            
            with patch('src.ai.action_executor.ActionExecutor'):
                ai_manager = AIGameManager(mock_game, {'ai_players': [0]})
                
                # Trigger jail decision
                ai_manager.event_listener._on_message_added({
                    'message': 'You are in jail. Pay the bail?',
                    'group': 'jail_options',
                    'player': 0
                })
                
                # Process
                context = ai_manager.decision_queue.get()
                decision = ai_manager._make_ai_decision(context)
                
                # Verify
                self.assertEqual(decision['action'], 'pay_fine')


if __name__ == '__main__':
    unittest.main()