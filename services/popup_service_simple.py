"""
Simple popup service that handles detection, analysis and AI decisions
"""
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional
from .event_bus import EventBus, EventTypes

class PopupService:
    """Manages popup detection, analysis and decisions"""
    
    def __init__(self, event_bus: EventBus, omniparser_url="http://localhost:8000"):
        self.event_bus = event_bus
        self.omniparser_url = omniparser_url
        self.active_popups = {}
        
    def register_popup(self, popup_data: dict) -> str:
        """Register a new detected popup"""
        popup_id = popup_data.get('id') or f"popup_{int(time.time() * 1000)}"
        
        popup_data['id'] = popup_id
        popup_data['detected_at'] = datetime.utcnow().isoformat()
        popup_data['status'] = 'detected'
        
        self.active_popups[popup_id] = popup_data
        
        print(f"[POPUP SERVICE] Registered popup: {popup_id}")
        
        # Publish event
        self.event_bus.publish(
            EventTypes.POPUP_DETECTED,
            popup_data,
            source='popup_service'
        )
        
        return popup_id
    
    def analyze_popup(self, popup_id: str, screenshot_base64: str) -> dict:
        """Analyze popup with OmniParser"""
        if popup_id not in self.active_popups:
            return {'success': False, 'error': f'Popup {popup_id} not found'}
        
        print(f"[POPUP SERVICE] Analyzing popup {popup_id} with OmniParser...")
        
        try:
            # Call OmniParser
            response = requests.post(
                f"{self.omniparser_url}/parse/",
                json={"base64_image": screenshot_base64},
                timeout=30
            )
            
            if response.ok:
                result = response.json()
                parsed_content = result.get('parsed_content_list', [])
                
                print(f"[POPUP SERVICE] OmniParser found {len(parsed_content)} elements")
                
                # Extract options
                options = []
                text_content = []
                
                for item in parsed_content:
                    if item.get('type') == 'text':
                        text = item.get('content', '')
                        text_content.append(text)
                        
                        # Check if it's a button
                        text_lower = text.lower()
                        button_keywords = ['yes', 'no', 'ok', 'cancel', 'buy', 'sell', 
                                         'continue', 'back', 'done', 'accept', 'decline']
                        
                        if any(keyword in text_lower for keyword in button_keywords):
                            options.append({
                                'name': text,
                                'bbox': item.get('bbox', []),
                                'confidence': item.get('confidence', 1.0)
                            })
                
                # Update popup data
                self.active_popups[popup_id]['options'] = options
                self.active_popups[popup_id]['text_content'] = text_content
                self.active_popups[popup_id]['status'] = 'analyzed'
                
                print(f"[POPUP SERVICE] Found options: {[opt['name'] for opt in options]}")
                
                # Publish event
                self.event_bus.publish(
                    EventTypes.POPUP_ANALYZED,
                    {
                        'popup_id': popup_id,
                        'options': options,
                        'text_content': text_content
                    },
                    source='popup_service'
                )
                
                return {'success': True, 'options': options, 'text_content': text_content}
            else:
                error_msg = f"OmniParser error: {response.status_code}"
                print(f"[POPUP SERVICE] {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error calling OmniParser: {str(e)}"
            print(f"[POPUP SERVICE] {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def request_ai_decision(self, popup_id: str, game_context: dict) -> None:
        """Request AI decision for popup"""
        if popup_id not in self.active_popups:
            return
        
        popup = self.active_popups[popup_id]
        
        print(f"[POPUP SERVICE] Requesting AI decision for popup {popup_id}")
        
        # Create decision request
        decision_request = {
            'popup_id': popup_id,
            'popup_text': ' '.join(popup.get('text_content', [])),
            'options': popup.get('options', []),
            'game_context': game_context
        }
        
        # Publish event for AI service
        self.event_bus.publish(
            EventTypes.AI_DECISION_REQUESTED,
            decision_request,
            source='popup_service'
        )
        
        # For now, make a simple decision based on keywords
        self._make_simple_decision(popup_id)
    
    def _make_simple_decision(self, popup_id: str):
        """Make a simple decision when AI is not available"""
        popup = self.active_popups[popup_id]
        options = popup.get('options', [])
        
        # Simple logic: prefer 'no' or 'cancel' for safety
        decision = None
        for option in options:
            name_lower = option['name'].lower()
            if 'no' in name_lower or 'cancel' in name_lower:
                decision = option
                break
        
        if not decision and options:
            decision = options[0]  # Take first option if no safe option found
        
        if decision:
            print(f"[POPUP SERVICE] Simple decision: clicking '{decision['name']}'")
            
            self.active_popups[popup_id]['decision'] = decision
            self.active_popups[popup_id]['status'] = 'decided'
            
            # Publish decision
            self.event_bus.publish(
                EventTypes.AI_DECISION_MADE,
                {
                    'popup_id': popup_id,
                    'decision': decision['name'],
                    'coordinates': decision.get('bbox', [])
                },
                source='popup_service'
            )
    
    def get_popup_status(self, popup_id: str) -> dict:
        """Get popup status"""
        if popup_id not in self.active_popups:
            return {'status': 'not_found'}
        
        popup = self.active_popups[popup_id]
        return {
            'status': popup.get('status', 'unknown'),
            'decision': popup.get('decision'),
            'options': popup.get('options', [])
        }
    
    def get_active_popups(self) -> dict:
        """Get all active popups"""
        return self.active_popups.copy()
    
    def execute_decision(self, popup_id: str, decision: str, coordinates: tuple) -> bool:
        """Execute a decision (mark as executed)"""
        if popup_id in self.active_popups:
            self.active_popups[popup_id]['status'] = 'executed'
            self.active_popups[popup_id]['executed_at'] = datetime.utcnow().isoformat()
            
            # Clean up after a delay
            # In production, you might want to do this differently
            if popup_id in self.active_popups:
                del self.active_popups[popup_id]
            
            return True
        return False