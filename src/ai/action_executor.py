"""
ActionExecutor - Executes AI decisions in the real game using OmniParser.

This module translates AI decisions into concrete actions (clicks, key presses)
using the OmniParser vision system to identify UI elements.
"""

import time
import json
import os
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import pyautogui
import requests
from PIL import Image
import io
import base64
import mss

from .game_event_listener import DecisionContext, DecisionType


@dataclass
class UIElement:
    """Represents a UI element found by OmniParser."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[int, int]


class ActionExecutor:
    """
    Executes AI decisions by interacting with the game UI.
    
    Uses OmniParser to identify UI elements and pyautogui to click them.
    """
    
    def __init__(self, omniparser_url: str = "http://localhost:8000"):
        """
        Initialize the ActionExecutor.
        
        Args:
            omniparser_url: URL of the OmniParser service
        """
        self.omniparser_url = omniparser_url
        self.screenshot_monitor = mss.mss()
        
        # UI element mappings for different actions
        self.action_mappings = {
            # Buy property actions
            'buy': ['Yes', 'Buy', 'Acheter', 'Oui', 'OK'],
            'pass': ['No', 'Pass', 'Non', 'Passer', 'Cancel'],
            
            # Jail actions
            'use_card': ['Use Card', 'Utiliser Carte', 'Get Out Free'],
            'pay_fine': ['Pay Fine', 'Payer Amende', 'Pay $50', 'Pay'],
            'roll': ['Roll Dice', 'Lancer Dés', 'Roll', 'Try Doubles'],
            
            # Auction actions
            'bid': ['Bid', 'Enchérir', 'Place Bid'],
            'pass_auction': ['Pass', 'Passer', 'No Bid'],
            
            # General actions
            'end_turn': ['End Turn', 'Fin Tour', 'Done', 'Terminer'],
            'roll_dice': ['Roll', 'Lancer', 'Roll Dice', 'Lancer les dés'],
            
            # Building actions
            'build': ['Build', 'Construire', 'Buy House', 'Acheter Maison'],
            'sell': ['Sell', 'Vendre', 'Sell House', 'Vendre Maison'],
            
            # Trade actions
            'accept': ['Accept', 'Accepter', 'Yes', 'Oui'],
            'decline': ['Decline', 'Refuser', 'No', 'Non'],
            
            # Navigation
            'ok': ['OK', 'Ok', 'Confirm', 'Confirmer'],
            'cancel': ['Cancel', 'Annuler', 'Back', 'Retour'],
        }
        
        # Safety delays to avoid clicking too fast
        self.click_delay = 0.5
        self.action_delay = 1.0
        
        # Last screenshot cache
        self.last_screenshot = None
        self.last_screenshot_time = 0
        self.screenshot_cache_duration = 0.5  # Cache for 500ms
    
    def execute_action(self, action: str, decision: Dict[str, Any], 
                      context: DecisionContext) -> bool:
        """
        Execute an action based on the AI's decision.
        
        Args:
            action: The action to perform
            decision: The full decision data from AI
            context: The decision context
            
        Returns:
            bool: True if action was executed successfully
        """
        try:
            # Map decision type and action to specific execution
            if context.decision_type == DecisionType.BUY_PROPERTY:
                return self._execute_buy_property(action, decision)
            
            elif context.decision_type == DecisionType.JAIL_STRATEGY:
                return self._execute_jail_action(action, decision)
            
            elif context.decision_type == DecisionType.AUCTION_BID:
                return self._execute_auction_action(action, decision)
            
            elif context.decision_type == DecisionType.BUILD_HOUSES:
                return self._execute_build_action(action, decision)
            
            elif context.decision_type == DecisionType.ROLL_DICE:
                return self._execute_roll_dice()
            
            elif context.decision_type == DecisionType.TRADE_RESPONSE:
                return self._execute_trade_response(action, decision)
            
            elif context.decision_type == DecisionType.GENERAL_ACTION:
                return self._execute_general_action(action, decision)
            
            else:
                print(f"[ActionExecutor] Unhandled decision type: {context.decision_type}")
                return False
                
        except Exception as e:
            print(f"[ActionExecutor] Error executing action: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _execute_buy_property(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute buy property decision."""
        if action == 'buy':
            return self._click_button(['Yes', 'Buy', 'Acheter', 'Oui'])
        else:
            return self._click_button(['No', 'Pass', 'Non', 'Passer'])
    
    def _execute_jail_action(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute jail strategy."""
        if action == 'use_card':
            return self._click_button(self.action_mappings['use_card'])
        elif action == 'pay_fine':
            return self._click_button(self.action_mappings['pay_fine'])
        else:  # roll
            return self._click_button(self.action_mappings['roll'])
    
    def _execute_auction_action(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute auction action."""
        if action == 'bid':
            # First, we might need to enter the bid amount
            bid_amount = decision.get('amount', 0)
            if bid_amount > 0:
                # Find and click bid input field
                input_clicked = self._click_button(['Bid Amount', 'Montant', 'Amount'])
                if input_clicked:
                    time.sleep(0.5)
                    # Clear existing and type new amount
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.typewrite(str(bid_amount))
                    time.sleep(0.3)
            
            # Click bid button
            return self._click_button(self.action_mappings['bid'])
        else:
            return self._click_button(self.action_mappings['pass_auction'])
    
    def _execute_build_action(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute build houses action."""
        if action == 'build':
            builds = decision.get('builds', [])
            if builds:
                # Click on build button
                return self._click_button(self.action_mappings['build'])
        elif action == 'skip':
            # Click done or cancel
            return self._click_button(self.action_mappings['end_turn'])
        
        return False
    
    def _execute_roll_dice(self) -> bool:
        """Execute roll dice action."""
        return self._click_button(self.action_mappings['roll_dice'])
    
    def _execute_trade_response(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute trade response."""
        if action == 'accept':
            return self._click_button(self.action_mappings['accept'])
        else:
            return self._click_button(self.action_mappings['decline'])
    
    def _execute_general_action(self, action: str, decision: Dict[str, Any]) -> bool:
        """Execute general action."""
        if action == 'end_turn':
            return self._click_button(self.action_mappings['end_turn'])
        else:
            # Try to find OK or Done button
            return self._click_button(self.action_mappings['ok'])
    
    def _click_button(self, button_labels: List[str]) -> bool:
        """
        Find and click a button with one of the given labels.
        
        Args:
            button_labels: List of possible button labels to look for
            
        Returns:
            bool: True if button was found and clicked
        """
        # Get current screenshot
        screenshot = self._get_screenshot()
        if screenshot is None:
            return False
        
        # Find UI elements using OmniParser
        elements = self._find_ui_elements(screenshot)
        
        # Look for matching button
        for element in elements:
            for label in button_labels:
                if label.lower() in element.label.lower():
                    print(f"[ActionExecutor] Found button '{element.label}' at {element.center}")
                    
                    # Click the button
                    self._perform_click(element.center)
                    return True
        
        print(f"[ActionExecutor] Could not find button with labels: {button_labels}")
        return False
    
    def _get_screenshot(self) -> Optional[Image.Image]:
        """Get a screenshot of the game window."""
        current_time = time.time()
        
        # Use cached screenshot if recent
        if (self.last_screenshot is not None and 
            current_time - self.last_screenshot_time < self.screenshot_cache_duration):
            return self.last_screenshot
        
        try:
            # Capture entire screen for now
            # TODO: Could be optimized to capture only game window
            screenshot = self.screenshot_monitor.grab(self.screenshot_monitor.monitors[0])
            
            # Convert to PIL Image
            img = Image.frombytes(
                'RGB',
                (screenshot.width, screenshot.height),
                screenshot.rgb
            )
            
            # Cache the screenshot
            self.last_screenshot = img
            self.last_screenshot_time = current_time
            
            return img
            
        except Exception as e:
            print(f"[ActionExecutor] Error capturing screenshot: {e}")
            return None
    
    def _find_ui_elements(self, screenshot: Image.Image) -> List[UIElement]:
        """
        Use OmniParser to find UI elements in the screenshot.
        
        Args:
            screenshot: PIL Image of the screen
            
        Returns:
            List of UIElement objects found
        """
        try:
            # Convert image to base64
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Call OmniParser API
            response = requests.post(
                f"{self.omniparser_url}/process",
                json={
                    "image": img_base64,
                    "prompt": "Find all buttons, clickable elements, and text labels"
                },
                timeout=5.0
            )
            
            if response.status_code != 200:
                print(f"[ActionExecutor] OmniParser error: {response.status_code}")
                return []
            
            # Parse response
            data = response.json()
            elements = []
            
            for item in data.get('elements', []):
                bbox = item.get('bbox', [])
                if len(bbox) == 4:
                    element = UIElement(
                        label=item.get('label', ''),
                        confidence=item.get('confidence', 0.0),
                        bbox=tuple(bbox),
                        center=(
                            (bbox[0] + bbox[2]) // 2,
                            (bbox[1] + bbox[3]) // 2
                        )
                    )
                    elements.append(element)
            
            return elements
            
        except requests.exceptions.RequestException as e:
            print(f"[ActionExecutor] Error calling OmniParser: {e}")
            # Fall back to template matching or OCR if OmniParser fails
            return self._fallback_find_elements(screenshot)
        except Exception as e:
            print(f"[ActionExecutor] Unexpected error in find_ui_elements: {e}")
            return []
    
    def _fallback_find_elements(self, screenshot: Image.Image) -> List[UIElement]:
        """
        Fallback method to find UI elements if OmniParser is unavailable.
        Uses template matching or OCR.
        """
        # This is a simplified fallback
        # In production, you might use OpenCV template matching or pytesseract OCR
        print("[ActionExecutor] Using fallback element detection")
        
        # For now, return empty list
        # TODO: Implement proper fallback
        return []
    
    def _perform_click(self, position: Tuple[int, int]):
        """
        Perform a click at the given position.
        
        Args:
            position: (x, y) coordinates to click
        """
        try:
            # Move to position
            pyautogui.moveTo(position[0], position[1], duration=0.2)
            time.sleep(self.click_delay)
            
            # Click
            pyautogui.click()
            
            # Wait after click
            time.sleep(self.action_delay)
            
            print(f"[ActionExecutor] Clicked at position {position}")
            
        except Exception as e:
            print(f"[ActionExecutor] Error performing click: {e}")
    
    def type_text(self, text: str):
        """
        Type text using the keyboard.
        
        Args:
            text: Text to type
        """
        try:
            pyautogui.typewrite(text, interval=0.05)
            time.sleep(0.5)
        except Exception as e:
            print(f"[ActionExecutor] Error typing text: {e}")
    
    def press_key(self, key: str):
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., 'enter', 'esc')
        """
        try:
            pyautogui.press(key)
            time.sleep(0.5)
        except Exception as e:
            print(f"[ActionExecutor] Error pressing key: {e}")
    
    def verify_action_completed(self, expected_result: str) -> bool:
        """
        Verify that an action was completed successfully.
        
        Args:
            expected_result: What to look for to confirm action completed
            
        Returns:
            bool: True if action appears to have completed
        """
        # Wait a bit for UI to update
        time.sleep(1.0)
        
        # Take new screenshot
        screenshot = self._get_screenshot()
        if screenshot is None:
            return False
        
        # Look for confirmation elements
        elements = self._find_ui_elements(screenshot)
        
        for element in elements:
            if expected_result.lower() in element.label.lower():
                return True
        
        return False