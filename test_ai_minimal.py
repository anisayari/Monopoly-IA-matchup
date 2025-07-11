#!/usr/bin/env python3
"""
Minimal test runner for AI module - runs basic tests without threading issues.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, Mock, patch

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock external dependencies
sys.modules['dolphin_memory_engine'] = MagicMock()
sys.modules['win32api'] = MagicMock()
sys.modules['win32con'] = MagicMock()
sys.modules['win32process'] = MagicMock()
sys.modules['win32gui'] = MagicMock()
sys.modules['pyautogui'] = MagicMock()
sys.modules['mss'] = MagicMock()

# Import our AI modules directly (without game dependencies)
from src.ai.game_event_listener import DecisionType, DecisionContext
from src.ai.action_executor import UIElement

def test_decision_types():
    """Test DecisionType enum."""
    print("\n=== Testing Decision Types ===")
    
    # Test all decision types exist
    expected_types = [
        'buy_property', 'jail_strategy', 'build_houses',
        'mortgage_property', 'trade_offer', 'trade_response',
        'auction_bid', 'general_action', 'roll_dice'
    ]
    
    actual_types = [dt.value for dt in DecisionType]
    
    for expected in expected_types:
        if expected in actual_types:
            print(f"✓ DecisionType.{expected}")
        else:
            print(f"✗ Missing DecisionType.{expected}")
    
    return len(expected_types) == len([e for e in expected_types if e in actual_types])

def test_decision_context():
    """Test DecisionContext creation."""
    print("\n=== Testing Decision Context ===")
    
    try:
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0,
            data={'property': 'Park Place'},
            message='Buy Park Place?'
        )
        
        print(f"✓ Created context: {context.decision_type.value}")
        print(f"✓ Player ID: {context.player_id}")
        print(f"✓ Message: {context.message}")
        print(f"✓ Has timestamp: {context.timestamp > 0}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create context: {e}")
        return False

def test_ui_element():
    """Test UIElement creation."""
    print("\n=== Testing UI Element ===")
    
    try:
        element = UIElement(
            label="Buy Button",
            confidence=0.95,
            bbox=(100, 200, 200, 250),
            center=(150, 225)
        )
        
        print(f"✓ Created element: {element.label}")
        print(f"✓ Confidence: {element.confidence}")
        print(f"✓ Bounding box: {element.bbox}")
        print(f"✓ Center: {element.center}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to create element: {e}")
        return False

def test_event_listener_basics():
    """Test basic GameEventListener functionality."""
    print("\n=== Testing Event Listener Basics ===")
    
    try:
        # Import with mocked game
        with patch('src.ai.game_event_listener.threading.Thread'):
            from src.ai.game_event_listener import GameEventListener
            
            # Create mock game
            mock_game = Mock()
            mock_game.listeners = Mock()
            mock_game.contexte = Mock()
            mock_game.contexte.state = {'current_player': 0}
            
            # Create listener
            listener = GameEventListener(mock_game)
            
            print("✓ GameEventListener created")
            
            # Test decision patterns
            patterns = listener.decision_patterns
            print(f"✓ Found {len(patterns)} decision patterns")
            
            # Test decision detection
            decision_type = listener._detect_decision_type(
                "Do you want to buy Park Place?", 
                "property_offer"
            )
            print(f"✓ Detected decision type: {decision_type}")
            
            return True
            
    except Exception as e:
        print(f"✗ Event listener test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_action_executor_basics():
    """Test basic ActionExecutor functionality."""
    print("\n=== Testing Action Executor Basics ===")
    
    try:
        from src.ai.action_executor import ActionExecutor
        
        executor = ActionExecutor()
        
        print("✓ ActionExecutor created")
        print(f"✓ OmniParser URL: {executor.omniparser_url}")
        print(f"✓ Action mappings: {len(executor.action_mappings)} defined")
        
        # Test action mappings
        important_actions = ['buy', 'pass', 'roll_dice', 'end_turn']
        for action in important_actions:
            if action in executor.action_mappings:
                print(f"✓ Action '{action}' mapped")
            else:
                print(f"✗ Action '{action}' not mapped")
        
        return True
        
    except Exception as e:
        print(f"✗ Action executor test failed: {e}")
        return False

def main():
    """Run all minimal tests."""
    print("Monopoly AI - Minimal Test Suite")
    print("================================")
    
    tests = [
        test_decision_types,
        test_decision_context,
        test_ui_element,
        test_event_listener_basics,
        test_action_executor_basics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n================================")
    print(f"Results: {passed} passed, {failed} failed")
    print("================================")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())