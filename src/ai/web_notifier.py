"""
Web Notifier - Sends AI events and decisions to the web launcher
"""

import requests
import json
from typing import Dict, Any
from datetime import datetime


class WebNotifier:
    """Send notifications to the web launcher."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.enabled = True
    
    def send_event(self, event_type: str, message: str, player: int = None, data: Dict[str, Any] = None):
        """Send a game event to the web interface."""
        if not self.enabled:
            return
        
        try:
            payload = {
                "type": event_type,
                "message": message,
                "player": player,
                "data": data or {}
            }
            
            response = requests.post(
                f"{self.base_url}/api/events/add",
                json=payload,
                timeout=1
            )
            
        except Exception as e:
            # Silently fail if web interface is not running
            pass
    
    def send_decision(self, player: int, decision_type: str, decision: str, 
                     reason: str = None, confidence: float = None, 
                     action_required: bool = False, action_info: Dict[str, Any] = None):
        """Send an AI decision to the web interface."""
        if not self.enabled:
            return
        
        try:
            payload = {
                "player": player,
                "type": decision_type,
                "decision": decision,
                "reason": reason,
                "confidence": confidence,
                "action_required": action_required
            }
            
            if action_required and action_info:
                payload.update({
                    "action_type": action_info.get("type"),
                    "action_target": action_info.get("target"),
                    "action_instructions": action_info.get("instructions")
                })
            
            response = requests.post(
                f"{self.base_url}/api/decisions/add",
                json=payload,
                timeout=1
            )
            
        except Exception as e:
            # Silently fail if web interface is not running
            pass
    
    def complete_action(self, action_id: str = None):
        """Mark an action as completed."""
        if not self.enabled:
            return
        
        try:
            payload = {"action_id": action_id} if action_id else {}
            
            response = requests.post(
                f"{self.base_url}/api/actions/complete",
                json=payload,
                timeout=1
            )
            
        except Exception as e:
            pass


# Global instance
web_notifier = WebNotifier()