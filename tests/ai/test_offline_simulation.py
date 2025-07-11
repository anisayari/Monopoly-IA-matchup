"""
Offline simulation tests - Test AI system without external dependencies.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.ai.mock_helpers import (
    MockMonopolyGame, MockOpenAIAgent, MockOmniParserResponse,
    create_test_game_state, simulate_game_events
)
from src.ai.game_event_listener import DecisionContext, DecisionType
from src.ai.ai_game_manager import AIGameManager
from src.ai.action_executor import UIElement


class TestOfflineSimulation(unittest.TestCase):
    """Test AI system in offline simulation mode."""
    
    def test_complete_turn_simulation(self):
        """Simulate a complete turn offline."""
        # Create mock game
        game = MockMonopolyGame(num_players=4)
        game.contexte.state = create_test_game_state('property_purchase')
        
        # Create mock AI agent
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent', MockOpenAIAgent):
            with patch('src.ai.action_executor.requests') as mock_requests:
                # Mock OmniParser responses
                mock_requests.post.return_value.status_code = 200
                mock_requests.post.return_value.json.return_value = MockOmniParserResponse.create_response([
                    MockOmniParserResponse.create_button_element('Buy', 100, 200),
                    MockOmniParserResponse.create_button_element('Pass', 250, 200)
                ])
                
                # Create AI manager
                ai_config = {'ai_players': [0], 'openai_api_key': 'mock-key'}
                ai_manager = AIGameManager(game, ai_config)
                
                # Simulate game events
                events = [
                    {
                        'type': 'message',
                        'data': {
                            'message': 'Do you want to buy Mediterranean Avenue for $60?',
                            'group': 'property_offer',
                            'player': 0
                        }
                    }
                ]
                
                # Process events
                simulate_game_events(ai_manager.event_listener, events)
                
                # Verify decision was queued
                self.assertEqual(ai_manager.decision_queue.qsize(), 1)
                
                # Get the decision
                context = ai_manager.decision_queue.get()
                self.assertEqual(context.decision_type, DecisionType.BUY_PROPERTY)
                
                # Verify AI agent was created with mock
                ai_player = ai_manager.ai_players[0]
                self.assertIsInstance(ai_player.agent, MockOpenAIAgent)
    
    def test_auction_scenario_offline(self):
        """Test auction scenario without external dependencies."""
        game = MockMonopolyGame()
        game.contexte.state = create_test_game_state('auction')
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent') as mock_agent_class:
            # Create aggressive bidder
            mock_agent = MockOpenAIAgent(0, strategy='aggressive')
            mock_agent_class.return_value = mock_agent
            
            with patch('src.ai.action_executor.pyautogui'):
                ai_manager = AIGameManager(game, {'ai_players': [0]})
                
                # Trigger auction
                game.listeners.emit('auction_started', {
                    'property': 'Boardwalk',
                    'starting_bid': 100
                })
                
                # Process decision
                context = ai_manager.decision_queue.get()
                decision = ai_manager._make_ai_decision(context)
                
                # Verify aggressive bid
                self.assertEqual(decision['action'], 'bid')
                self.assertGreater(decision['amount'], 100)
    
    def test_jail_scenario_offline(self):
        """Test jail decision without external dependencies."""
        game = MockMonopolyGame()
        game.contexte.state = create_test_game_state('jail')
        
        # Test with get out of jail card
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent', MockOpenAIAgent):
            ai_manager = AIGameManager(game, {'ai_players': [0]})
            
            # Simulate jail message
            game.listeners.emit('message_added', {
                'message': 'You are in jail. Use jail free card?',
                'group': 'jail_options',
                'player': 0
            })
            
            # Create context with card
            context = ai_manager.decision_queue.get()
            context.data['has_card'] = True
            
            # Initialize sim for decision
            ai_manager._initialize_simulation(game.contexte.state)
            
            # Make decision
            decision = ai_manager._decide_jail_strategy(
                ai_manager.ai_players[0], 
                context
            )
            
            # Should use card
            self.assertEqual(decision['action'], 'use_card')
    
    def test_ui_element_detection_offline(self):
        """Test UI element detection simulation."""
        from src.ai.action_executor import ActionExecutor
        
        executor = ActionExecutor()
        
        # Mock OmniParser response
        with patch('src.ai.action_executor.requests') as mock_requests:
            mock_requests.post.return_value.status_code = 200
            mock_requests.post.return_value.json.return_value = {
                'elements': [
                    {
                        'label': 'Buy Property',
                        'confidence': 0.95,
                        'bbox': [100, 200, 200, 240]
                    },
                    {
                        'label': 'Pass',
                        'confidence': 0.92,
                        'bbox': [250, 200, 320, 240]
                    }
                ]
            }
            
            # Create mock image
            from PIL import Image
            mock_image = Image.new('RGB', (800, 600))
            
            # Find elements
            elements = executor._find_ui_elements(mock_image)
            
            # Verify elements found
            self.assertEqual(len(elements), 2)
            self.assertEqual(elements[0].label, 'Buy Property')
            self.assertEqual(elements[0].center, (150, 220))
    
    def test_state_sync_offline(self):
        """Test state synchronization offline."""
        game = MockMonopolyGame()
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent', MockOpenAIAgent):
            ai_manager = AIGameManager(game, {'ai_players': [0]})
            
            # Initial state
            initial_money = game.contexte.state['player_money']['0']
            
            # Simulate property purchase
            game.contexte.state['player_money']['0'] = initial_money - 60
            game.contexte.state['properties']['1'] = {
                'owner': 0,
                'name': 'Mediterranean Avenue'
            }
            
            # Force sync
            ai_manager.last_sync_time = 0
            ai_manager._sync_game_state()
            
            # Verify simulation updated
            if ai_manager.sim_game:
                player = ai_manager.sim_game.players[0]
                self.assertEqual(player.money, initial_money - 60)
                self.assertGreater(len(player.properties), 0)
    
    def test_decision_patterns_offline(self):
        """Test various decision patterns offline."""
        game = MockMonopolyGame()
        
        test_messages = [
            ('Do you want to buy Park Place?', DecisionType.BUY_PROPERTY),
            ('Pay $50 to get out of jail?', DecisionType.JAIL_STRATEGY),
            ('Build houses on which property?', DecisionType.BUILD_HOUSES),
            ('Current bid is $200', DecisionType.AUCTION_BID),
            ('What would you like to do?', DecisionType.GENERAL_ACTION)
        ]
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent', MockOpenAIAgent):
            ai_manager = AIGameManager(game, {'ai_players': [0]})
            
            for message, expected_type in test_messages:
                # Clear queue
                while not ai_manager.decision_queue.empty():
                    ai_manager.decision_queue.get()
                
                # Emit message
                game.listeners.emit('message_added', {
                    'message': message,
                    'group': '',
                    'player': 0
                })
                
                # Check decision type
                if not ai_manager.decision_queue.empty():
                    context = ai_manager.decision_queue.get()
                    self.assertEqual(
                        context.decision_type, 
                        expected_type,
                        f"Failed for message: {message}"
                    )
    
    def test_multi_player_ai_offline(self):
        """Test multiple AI players offline."""
        game = MockMonopolyGame()
        
        # Configure 2 AI players with different strategies
        ai_config = {
            'ai_players': [0, 2],
            'openai_api_key': 'mock-key'
        }
        
        with patch('src.ai.ai_game_manager.OpenAIMonopolyAgent') as mock_agent_class:
            # Create different strategies
            def create_agent(player_id, *args, **kwargs):
                if player_id == 0:
                    return MockOpenAIAgent(player_id, 'aggressive')
                else:
                    return MockOpenAIAgent(player_id, 'conservative')
            
            mock_agent_class.side_effect = create_agent
            
            ai_manager = AIGameManager(game, ai_config)
            
            # Trigger decisions for both
            for player_id in [0, 2]:
                game.contexte.state['current_player'] = player_id
                game.listeners.emit('message_added', {
                    'message': 'Buy Boardwalk for $400?',
                    'group': 'property_offer',
                    'player': player_id
                })
            
            # Process decisions
            decisions = []
            while not ai_manager.decision_queue.empty():
                context = ai_manager.decision_queue.get()
                ai_manager._initialize_simulation(game.contexte.state)
                decision = ai_manager._make_ai_decision(context)
                decisions.append((context.player_id, decision))
            
            # Verify different strategies
            self.assertEqual(len(decisions), 2)
            # Player 0 (aggressive) should buy
            self.assertTrue(any(d[1]['action'] == 'buy' for d in decisions if d[0] == 0))
            # Player 2 (conservative) should pass
            self.assertTrue(any(d[1]['action'] == 'pass' for d in decisions if d[0] == 2))


if __name__ == '__main__':
    unittest.main()