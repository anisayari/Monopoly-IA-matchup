"""
Unit tests for ActionExecutor - Test action execution and UI interaction.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from PIL import Image
import io

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.ai.action_executor import ActionExecutor, UIElement
from src.ai.game_event_listener import DecisionContext, DecisionType


class TestActionExecutor(unittest.TestCase):
    """Test ActionExecutor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.executor = ActionExecutor("http://localhost:8000")
        
        # Mock pyautogui to prevent actual clicks
        self.pyautogui_patcher = patch('src.ai.action_executor.pyautogui')
        self.mock_pyautogui = self.pyautogui_patcher.start()
        
        # Mock mss for screenshots
        self.mss_patcher = patch('src.ai.action_executor.mss')
        self.mock_mss = self.mss_patcher.start()
        
        # Mock requests for OmniParser
        self.requests_patcher = patch('src.ai.action_executor.requests')
        self.mock_requests = self.requests_patcher.start()
    
    def tearDown(self):
        """Clean up patches."""
        self.pyautogui_patcher.stop()
        self.mss_patcher.stop()
        self.requests_patcher.stop()
    
    def test_initialization(self):
        """Test ActionExecutor initialization."""
        self.assertEqual(self.executor.omniparser_url, "http://localhost:8000")
        self.assertEqual(self.executor.click_delay, 0.5)
        self.assertEqual(self.executor.action_delay, 1.0)
        self.assertIsNone(self.executor.last_screenshot)
    
    def test_ui_element_creation(self):
        """Test UIElement dataclass."""
        element = UIElement(
            label="Buy",
            confidence=0.95,
            bbox=(100, 200, 150, 250),
            center=(125, 225)
        )
        
        self.assertEqual(element.label, "Buy")
        self.assertEqual(element.confidence, 0.95)
        self.assertEqual(element.bbox, (100, 200, 150, 250))
        self.assertEqual(element.center, (125, 225))
    
    def test_execute_buy_property(self):
        """Test executing buy property action."""
        # Mock finding and clicking button
        self.executor._click_button = Mock(return_value=True)
        
        decision = {'action': 'buy', 'property': 'Park Place'}
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0
        )
        
        result = self.executor.execute_action('buy', decision, context)
        
        self.assertTrue(result)
        self.executor._click_button.assert_called_once()
        
        # Test pass action
        self.executor._click_button.reset_mock()
        result = self.executor.execute_action('pass', decision, context)
        
        self.assertTrue(result)
        self.executor._click_button.assert_called_once()
    
    def test_execute_jail_action(self):
        """Test executing jail actions."""
        self.executor._click_button = Mock(return_value=True)
        
        context = DecisionContext(
            decision_type=DecisionType.JAIL_STRATEGY,
            player_id=0
        )
        
        # Test use card
        decision = {'action': 'use_card'}
        result = self.executor.execute_action('use_card', decision, context)
        self.assertTrue(result)
        
        # Test pay fine
        decision = {'action': 'pay_fine'}
        result = self.executor.execute_action('pay_fine', decision, context)
        self.assertTrue(result)
        
        # Test roll
        decision = {'action': 'roll'}
        result = self.executor.execute_action('roll', decision, context)
        self.assertTrue(result)
    
    def test_execute_auction_action(self):
        """Test executing auction actions."""
        self.executor._click_button = Mock(return_value=True)
        self.mock_pyautogui.typewrite = Mock()
        
        context = DecisionContext(
            decision_type=DecisionType.AUCTION_BID,
            player_id=0
        )
        
        # Test bid with amount
        decision = {'action': 'bid', 'amount': 500}
        result = self.executor.execute_action('bid', decision, context)
        
        self.assertTrue(result)
        self.mock_pyautogui.typewrite.assert_called_with('500')
    
    def test_get_screenshot(self):
        """Test screenshot capture."""
        # Mock screenshot
        mock_screenshot = Mock()
        mock_screenshot.width = 1920
        mock_screenshot.height = 1080
        mock_screenshot.rgb = b'\x00' * (1920 * 1080 * 3)
        
        mock_monitor = Mock()
        self.executor.screenshot_monitor.monitors = [mock_monitor]
        self.executor.screenshot_monitor.grab.return_value = mock_screenshot
        
        # Get screenshot
        screenshot = self.executor._get_screenshot()
        
        self.assertIsInstance(screenshot, Image.Image)
        self.assertEqual(screenshot.size, (1920, 1080))
        
        # Test caching
        screenshot2 = self.executor._get_screenshot()
        self.assertEqual(screenshot, screenshot2)  # Should be cached
    
    def test_find_ui_elements(self):
        """Test finding UI elements with OmniParser."""
        # Create test image
        test_image = Image.new('RGB', (100, 100), color='white')
        
        # Mock OmniParser response
        self.mock_requests.post.return_value.status_code = 200
        self.mock_requests.post.return_value.json.return_value = {
            'elements': [
                {
                    'label': 'Buy Button',
                    'confidence': 0.95,
                    'bbox': [10, 20, 50, 40]
                },
                {
                    'label': 'Cancel',
                    'confidence': 0.89,
                    'bbox': [60, 20, 90, 40]
                }
            ]
        }
        
        elements = self.executor._find_ui_elements(test_image)
        
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].label, 'Buy Button')
        self.assertEqual(elements[0].center, (30, 30))
        self.assertEqual(elements[1].label, 'Cancel')
    
    def test_find_ui_elements_fallback(self):
        """Test fallback when OmniParser fails."""
        test_image = Image.new('RGB', (100, 100))
        
        # Mock OmniParser failure
        self.mock_requests.post.side_effect = Exception("Connection error")
        
        elements = self.executor._find_ui_elements(test_image)
        
        # Should return empty list from fallback
        self.assertEqual(elements, [])
    
    def test_click_button(self):
        """Test button clicking logic."""
        # Mock screenshot and elements
        self.executor._get_screenshot = Mock(return_value=Image.new('RGB', (100, 100)))
        self.executor._find_ui_elements = Mock(return_value=[
            UIElement('Yes', 0.95, (10, 10, 50, 30), (30, 20)),
            UIElement('No', 0.90, (60, 10, 90, 30), (75, 20))
        ])
        self.executor._perform_click = Mock()
        
        # Click "Yes" button
        result = self.executor._click_button(['Yes', 'Oui', 'OK'])
        
        self.assertTrue(result)
        self.executor._perform_click.assert_called_once_with((30, 20))
        
        # Test no matching button
        self.executor._find_ui_elements.return_value = []
        result = self.executor._click_button(['NonExistent'])
        
        self.assertFalse(result)
    
    def test_perform_click(self):
        """Test click performance."""
        position = (100, 200)
        
        self.executor._perform_click(position)
        
        self.mock_pyautogui.moveTo.assert_called_once_with(100, 200, duration=0.2)
        self.mock_pyautogui.click.assert_called_once()
    
    def test_type_text(self):
        """Test text typing."""
        self.executor.type_text("Hello World")
        
        self.mock_pyautogui.typewrite.assert_called_once_with("Hello World", interval=0.05)
    
    def test_press_key(self):
        """Test key pressing."""
        self.executor.press_key("enter")
        
        self.mock_pyautogui.press.assert_called_once_with("enter")
    
    def test_error_handling(self):
        """Test error handling in action execution."""
        # Test with exception in execution
        self.executor._click_button = Mock(side_effect=Exception("Test error"))
        
        decision = {'action': 'buy'}
        context = DecisionContext(
            decision_type=DecisionType.BUY_PROPERTY,
            player_id=0
        )
        
        # Should not crash
        result = self.executor.execute_action('buy', decision, context)
        
        self.assertFalse(result)
    
    def test_action_mappings(self):
        """Test action mapping definitions."""
        # Check important mappings exist
        self.assertIn('buy', self.executor.action_mappings)
        self.assertIn('pass', self.executor.action_mappings)
        self.assertIn('use_card', self.executor.action_mappings)
        self.assertIn('pay_fine', self.executor.action_mappings)
        self.assertIn('bid', self.executor.action_mappings)
        self.assertIn('end_turn', self.executor.action_mappings)
        
        # Check mappings have multiple options
        self.assertIsInstance(self.executor.action_mappings['buy'], list)
        self.assertGreater(len(self.executor.action_mappings['buy']), 1)


if __name__ == '__main__':
    unittest.main()