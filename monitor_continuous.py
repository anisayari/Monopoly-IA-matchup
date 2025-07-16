#!/usr/bin/env python3
"""
Continuous Game Monitor with AI Decision System
Monitors RAM continuously for game state and popup detection
"""

import sys
import os
import time
import json
import base64
import requests
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import threading
import queue
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.memory_reader import MemoryReader
from src.game.monopoly import MonopolyGame
from src.game.contexte import Contexte
import dolphin_memory_engine as dme
import pyautogui
from mss import mss
from PIL import Image
import io

class ContinuousGameMonitor:
    """Continuously monitors game state and handles popups with AI decisions"""
    
    def __init__(self):
        self.memory_reader = MemoryReader()
        self.game = None
        self.running = False
        self.popup_queue = queue.Queue()
        self.last_popup_time = 0
        self.popup_cooldown = 2.0  # seconds between popup checks
        
        # Idle detection
        self.last_state_change = time.time()
        self.idle_timeout = 120.0  # 2 minutes
        self.last_game_state_hash = None
        self.idle_check_triggered = False
        
        # Game context
        self.global_context = {
            "game_started": False,
            "current_turn": 0,
            "dice_values": [0, 0],
            "last_update": None
        }
        self.player_contexts = {}
        
        # Service URLs
        self.flask_url = "http://localhost:5000"
        self.omniparser_url = "http://localhost:8000"
        self.unified_url = "http://localhost:7000"
        
        # Screen capture
        self.sct = mss()
        
    def initialize(self) -> bool:
        """Initialize connection to Dolphin"""
        print("=" * 60)
        print("CONTINUOUS GAME MONITOR - INITIALIZATION")
        print("=" * 60)
        print()
        
        print("[1/3] Connecting to Dolphin Memory Engine...")
        if not dme.is_hooked():
            dme.hook()
            time.sleep(1)
            if not dme.is_hooked():
                print("  [ERROR] Failed to connect to Dolphin Memory Engine")
                print("  Make sure Dolphin is running with Monopoly loaded")
                return False
        print("  [OK] Connected to Dolphin")
        
        print("\n[2/3] Initializing Memory Reader...")
        print("  [OK] Memory Reader initialized")
        
        print("\n[3/3] Initializing Game Instance...")
        self.game = MonopolyGame(self.memory_reader)
        print("  [OK] Game instance created")
        
        print("\n" + "=" * 60)
        print("INITIALIZATION COMPLETE - Starting continuous monitoring...")
        print("=" * 60 + "\n")
        
        return True
    
    def read_game_state(self) -> Dict:
        """Read complete game state from memory"""
        try:
            state = {
                "timestamp": datetime.now().isoformat(),
                "players": [],
                "current_player": None,
                "dice": [0, 0],
                "properties": {},
                "game_phase": "unknown"
            }
            
            # Read player data
            for i in range(4):  # Max 4 players
                try:
                    player_data = {
                        "id": i,
                        "money": self.memory_reader.read_player_money(i),
                        "position": self.memory_reader.read_player_position(i),
                        "properties": [],
                        "in_jail": False,
                        "active": False
                    }
                    
                    # Check if player is active (has money or position)
                    if player_data["money"] > 0 or player_data["position"] > 0:
                        player_data["active"] = True
                        state["players"].append(player_data)
                except:
                    pass
            
            # Read dice values
            try:
                dice1 = self.memory_reader.read_memory(0x80000000 + 0x123456, 1)[0]  # Example addresses
                dice2 = self.memory_reader.read_memory(0x80000000 + 0x123457, 1)[0]
                state["dice"] = [dice1, dice2]
            except:
                pass
            
            # Detect current player
            try:
                current_player_index = self.memory_reader.read_memory(0x80000000 + 0x123458, 1)[0]
                state["current_player"] = current_player_index
            except:
                pass
            
            return state
        except Exception as e:
            print(f"[ERROR] Failed to read game state: {e}")
            return None
    
    def update_contexts(self, game_state: Dict):
        """Update global and per-player contexts"""
        if not game_state:
            return
        
        # Check if state has changed
        state_hash = self._calculate_state_hash(game_state)
        if state_hash != self.last_game_state_hash:
            self.last_state_change = time.time()
            self.last_game_state_hash = state_hash
            self.idle_check_triggered = False  # Reset idle check
        
        # Update global context
        self.global_context["last_update"] = game_state["timestamp"]
        self.global_context["dice_values"] = game_state["dice"]
        self.global_context["current_turn"] = game_state.get("current_player", 0)
        
        # Update player contexts
        for player in game_state.get("players", []):
            player_id = player["id"]
            if player_id not in self.player_contexts:
                self.player_contexts[player_id] = {
                    "id": player_id,
                    "money_history": [],
                    "position_history": [],
                    "properties": [],
                    "strategy": "balanced"
                }
            
            context = self.player_contexts[player_id]
            context["current_money"] = player["money"]
            context["current_position"] = player["position"]
            context["money_history"].append({
                "time": game_state["timestamp"],
                "amount": player["money"]
            })
            context["position_history"].append({
                "time": game_state["timestamp"],
                "position": player["position"]
            })
    
    def _calculate_state_hash(self, game_state: Dict) -> str:
        """Calculate a hash of the game state to detect changes"""
        # Create a simple hash from key game values
        key_values = []
        for player in game_state.get("players", []):
            key_values.extend([player["money"], player["position"]])
        key_values.extend(game_state.get("dice", [0, 0]))
        key_values.append(game_state.get("current_player", 0))
        return str(hash(tuple(key_values)))
    
    def detect_popup(self) -> bool:
        """Check if a popup is currently displayed"""
        try:
            # Method 1: Check known popup memory addresses
            popup_flags = [
                (0x80000000 + 0x2A8B60, 1),  # General popup flag
                (0x80000000 + 0x2A8B61, 1),  # Property purchase popup
                (0x80000000 + 0x2A8B62, 1),  # Trade popup
            ]
            
            for address, expected_value in popup_flags:
                value = self.memory_reader.read_memory(address, 1)[0]
                if value == expected_value:
                    return True
            
            return False
        except:
            return False
    
    def capture_screen(self) -> str:
        """Capture current screen and return as base64"""
        try:
            # Capture primary monitor
            monitor = self.sct.monitors[1]
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return img_str
        except Exception as e:
            print(f"[ERROR] Failed to capture screen: {e}")
            return None
    
    def process_popup_with_ai(self, screenshot_base64: str) -> Dict:
        """Process popup with AI to get decision"""
        print("\n" + "="*50)
        print("POPUP DETECTED - REQUESTING AI DECISION")
        print("="*50)
        
        try:
            # Build context for AI
            context = {
                "global_state": self.global_context,
                "player_contexts": self.player_contexts,
                "timestamp": datetime.now().isoformat()
            }
            
            # Use unified decision server if available
            if self.check_service_available(self.unified_url):
                print("\n[AI] Using Unified Decision Server...")
                response = requests.post(
                    f"{self.unified_url}/api/decision/unified",
                    json={
                        "image": screenshot_base64,
                        "context": context,
                        "type": "popup"
                    },
                    timeout=30
                )
                
                if response.ok:
                    result = response.json()
                    decision = result.get("decision", {})
                    parsed_elements = result.get("parsed_elements", {})
                    
                    print(f"\n[AI DECISION]")
                    print(f"  Action: {decision.get('action', 'unknown')}")
                    print(f"  Confidence: {decision.get('confidence', 0)}%")
                    print(f"  Reason: {decision.get('reason', 'No reason provided')}")
                    
                    # Find the button to click based on decision
                    if parsed_elements:
                        self.execute_ai_decision(decision, parsed_elements)
                    
                    return decision
            else:
                print("[WARNING] Unified Decision Server not available")
                # Fallback to direct OmniParser + simple decision
                return self.fallback_decision(screenshot_base64)
                
        except Exception as e:
            print(f"[ERROR] AI decision failed: {e}")
            return {"action": "no", "reason": "Error occurred"}
    
    def execute_ai_decision(self, decision: Dict, parsed_elements: Dict):
        """Execute the AI's decision by clicking the appropriate button"""
        action = decision.get("action", "").lower()
        parsed_content = parsed_elements.get("parsed_content_list", [])
        
        print(f"\n[EXECUTE] Looking for button matching action: {action}")
        
        # Map AI actions to button texts
        action_mappings = {
            "yes": ["yes", "ok", "confirm", "accept"],
            "no": ["no", "cancel", "decline", "back"],
            "buy": ["buy", "purchase", "buy property"],
            "sell": ["sell", "sell property"],
            "trade": ["trade", "deal", "propose"]
        }
        
        target_buttons = action_mappings.get(action, [action])
        
        # Find matching button in parsed elements
        for element in parsed_content:
            if element.get("type") == "text":
                element_text = element.get("content", "").lower()
                for target in target_buttons:
                    if target in element_text:
                        bbox = element.get("bbox", [])
                        if len(bbox) >= 4:
                            # Calculate click position (center of bbox)
                            x = (bbox[0] + bbox[2]) // 2
                            y = (bbox[1] + bbox[3]) // 2
                            
                            print(f"  [CLICK] Found '{element_text}' at ({x}, {y})")
                            pyautogui.click(x, y)
                            time.sleep(0.5)
                            return
        
        print("  [WARNING] No matching button found for action")
    
    def fallback_decision(self, screenshot_base64: str) -> Dict:
        """Simple fallback decision when AI is not available"""
        print("[FALLBACK] Using simple decision logic")
        # Always choose conservative options
        return {
            "action": "no",
            "confidence": 50,
            "reason": "AI service unavailable, choosing safe option"
        }
    
    def check_service_available(self, url: str) -> bool:
        """Check if a service is available"""
        try:
            response = requests.get(f"{url}/health", timeout=2)
            return response.ok
        except:
            return False
    
    def handle_idle_state(self):
        """Handle when game has been idle for too long"""
        print("\n" + "="*60)
        print("IDLE STATE DETECTED - NO CHANGES FOR 2 MINUTES")
        print("="*60)
        
        current_player = self.global_context.get("current_turn", 0)
        print(f"\n[IDLE] Current player: {current_player}")
        print("[IDLE] Triggering AI analysis to determine next action...")
        
        # Capture screen
        screenshot = self.capture_screen()
        if not screenshot:
            print("[ERROR] Failed to capture screen for idle analysis")
            return
        
        try:
            # Build enhanced context for idle situation
            context = {
                "global_state": self.global_context,
                "player_contexts": self.player_contexts,
                "timestamp": datetime.now().isoformat(),
                "idle_trigger": True,
                "idle_duration": time.time() - self.last_state_change,
                "current_player": current_player,
                "instruction": f"Game has been idle for 2 minutes. It's Player {current_player}'s turn. Analyze the screen and determine what action to take."
            }
            
            # Use unified decision server
            if self.check_service_available(self.unified_url):
                print("\n[AI] Requesting idle state analysis...")
                response = requests.post(
                    f"{self.unified_url}/api/decision/unified",
                    json={
                        "image": screenshot,
                        "context": context,
                        "type": "idle_action"
                    },
                    timeout=30
                )
                
                if response.ok:
                    result = response.json()
                    decision = result.get("decision", {})
                    parsed_elements = result.get("parsed_elements", {})
                    
                    print(f"\n[AI IDLE DECISION]")
                    print(f"  Action: {decision.get('action', 'unknown')}")
                    print(f"  Target: {decision.get('target', 'none')}")
                    print(f"  Reason: {decision.get('reason', 'No reason provided')}")
                    
                    # Execute the idle action
                    self.execute_idle_action(decision, parsed_elements)
                else:
                    print(f"[ERROR] AI service returned error: {response.status_code}")
            else:
                # Fallback: Try to find and click "Roll Dice" or similar common actions
                print("[FALLBACK] AI service unavailable, attempting default action...")
                self.execute_default_idle_action()
                
        except Exception as e:
            print(f"[ERROR] Failed to handle idle state: {e}")
    
    def execute_idle_action(self, decision: Dict, parsed_elements: Dict):
        """Execute action for idle state"""
        action = decision.get("action", "").lower()
        parsed_content = parsed_elements.get("parsed_content_list", [])
        
        print(f"\n[EXECUTE IDLE] Looking for elements to interact with...")
        
        # Common idle actions
        idle_actions = {
            "roll": ["roll dice", "roll", "lancer", "throw dice"],
            "end_turn": ["end turn", "next turn", "fin du tour"],
            "continue": ["continue", "ok", "next"],
            "menu": ["menu", "options", "settings"]
        }
        
        # Try to find and click based on AI decision
        for element in parsed_content:
            if element.get("type") == "text":
                element_text = element.get("content", "").lower()
                
                # Check if element matches our action
                for action_type, keywords in idle_actions.items():
                    if action == action_type or any(kw in element_text for kw in keywords):
                        bbox = element.get("bbox", [])
                        if len(bbox) >= 4:
                            x = (bbox[0] + bbox[2]) // 2
                            y = (bbox[1] + bbox[3]) // 2
                            print(f"  [CLICK] Found '{element_text}' at ({x}, {y})")
                            pyautogui.click(x, y)
                            time.sleep(1)
                            self.idle_check_triggered = True
                            return
        
        print("  [WARNING] No suitable action found on screen")
        
    def execute_default_idle_action(self):
        """Execute a default action when idle and no AI available"""
        print("[DEFAULT] Attempting to click in center of game area...")
        # Click in a safe area of the screen (customize based on your game)
        pyautogui.click(960, 540)  # Center of 1920x1080 screen
        time.sleep(1)
        self.idle_check_triggered = True
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("\n[MONITOR] Starting continuous monitoring...")
        print("  - Reading game state every 1 second")
        print("  - Checking for popups every 2 seconds")
        print("  - Idle detection after 2 minutes of no changes")
        print("  - Press Ctrl+C to stop\n")
        
        last_state_read = 0
        state_read_interval = 1.0  # Read state every second
        
        while self.running:
            try:
                current_time = time.time()
                
                # Read game state periodically
                if current_time - last_state_read >= state_read_interval:
                    game_state = self.read_game_state()
                    if game_state:
                        self.update_contexts(game_state)
                        
                        # Calculate idle time
                        idle_time = current_time - self.last_state_change
                        idle_status = f"Idle: {int(idle_time)}s" if idle_time > 10 else "Active"
                        
                        print(f"\r[STATE] Players: {len(game_state['players'])} | "
                              f"Current: P{game_state['current_player']} | "
                              f"Dice: {game_state['dice']} | "
                              f"{idle_status} | "
                              f"Time: {datetime.now().strftime('%H:%M:%S')}", end="")
                    last_state_read = current_time
                
                # Check for popups
                if current_time - self.last_popup_time >= self.popup_cooldown:
                    if self.detect_popup():
                        print("\n\n[ALERT] POPUP DETECTED!")
                        screenshot = self.capture_screen()
                        if screenshot:
                            self.process_popup_with_ai(screenshot)
                        self.last_popup_time = current_time
                
                # Check for idle state (2 minutes with no changes)
                if not self.idle_check_triggered and (current_time - self.last_state_change) >= self.idle_timeout:
                    self.handle_idle_state()
                    # Wait a bit before checking idle again
                    time.sleep(5)
                
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
            except KeyboardInterrupt:
                print("\n\n[MONITOR] Stopping...")
                break
            except Exception as e:
                print(f"\n[ERROR] Monitor loop error: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the monitoring system"""
        if not self.initialize():
            return False
        
        self.running = True
        
        try:
            self.monitor_loop()
        finally:
            self.stop()
    
    def stop(self):
        """Stop the monitoring system"""
        self.running = False
        if dme.is_hooked():
            dme.un_hook()
        print("\n[MONITOR] Stopped")
    
    def display_context_summary(self):
        """Display current context summary"""
        print("\n" + "="*60)
        print("GAME CONTEXT SUMMARY")
        print("="*60)
        
        print("\nGLOBAL CONTEXT:")
        print(f"  Game Started: {self.global_context['game_started']}")
        print(f"  Current Turn: Player {self.global_context['current_turn']}")
        print(f"  Last Dice: {self.global_context['dice_values']}")
        print(f"  Last Update: {self.global_context['last_update']}")
        
        print("\nPLAYER CONTEXTS:")
        for player_id, context in self.player_contexts.items():
            print(f"\n  Player {player_id}:")
            print(f"    Money: ${context.get('current_money', 0)}")
            print(f"    Position: {context.get('current_position', 0)}")
            print(f"    Properties: {len(context.get('properties', []))}")
            print(f"    Strategy: {context.get('strategy', 'unknown')}")


def main():
    """Main entry point"""
    print("MONOPOLY IA - CONTINUOUS MONITOR WITH AI")
    print("========================================")
    print()
    
    # Check if services are running
    monitor = ContinuousGameMonitor()
    
    print("Checking required services...")
    services_ok = True
    
    if not monitor.check_service_available("http://localhost:5000"):
        print("  [WARNING] Flask server not running")
        services_ok = False
    else:
        print("  [OK] Flask server")
    
    if not monitor.check_service_available("http://localhost:8000"):
        print("  [WARNING] OmniParser not running")
    else:
        print("  [OK] OmniParser")
    
    if not monitor.check_service_available("http://localhost:7000"):
        print("  [WARNING] Unified Decision Server not running")
        print("  [INFO] Will use fallback decisions")
    else:
        print("  [OK] Unified Decision Server")
    
    if not services_ok:
        print("\nSome services are not running. Start them with:")
        print("  start_all_services.bat")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print()
    monitor.start()


if __name__ == "__main__":
    main()