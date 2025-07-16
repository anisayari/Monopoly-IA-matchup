"""
Serveur unifié pour toutes les décisions tierces
Centralise les appels à OmniParser, AI Service, et autres services externes
"""

import asyncio
import aiohttp
from flask import Flask, request, jsonify
import requests
import logging
import os
from typing import Dict, Any, Optional
import base64
from io import BytesIO
from PIL import Image
import json
from datetime import datetime

class UnifiedDecisionServer:
    """Serveur unifié pour gérer toutes les décisions tierces"""
    
    def __init__(self, app: Flask = None):
        self.app = app or Flask(__name__)
        self.logger = logging.getLogger(__name__)
        self.services = {
            "omniparser": {
                "url": "http://localhost:8000",
                "endpoints": {
                    "parse": "/parse/",
                    "health": "/health"
                }
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1"
            }
        }
        self.setup_routes()
        
    def setup_routes(self):
        """Configure les routes du serveur unifié"""
        
        @self.app.route('/api/decision/parse', methods=['POST'])
        def parse_image():
            """Parse une image avec OmniParser"""
            try:
                data = request.json
                if not data or 'image' not in data:
                    return jsonify({'error': 'No image provided'}), 400
                    
                # Transmettre à OmniParser
                response = requests.post(
                    f"{self.services['omniparser']['url']}/parse/",
                    json={"image": data['image']}
                )
                
                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'result': response.json(),
                        'service': 'omniparser'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'OmniParser error: {response.status_code}'
                    }), response.status_code
                    
            except Exception as e:
                self.logger.error(f"Error parsing image: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
                
        @self.app.route('/api/decision/ai', methods=['POST'])
        def make_ai_decision():
            """Prend une décision IA basée sur le contexte"""
            try:
                data = request.json
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                    
                context = data.get('context', {})
                parsed_elements = data.get('parsed_elements', {})
                decision_type = data.get('type', 'popup')
                
                # Construire le prompt
                prompt = self._build_ai_prompt(context, parsed_elements, decision_type)
                
                # Appeler OpenAI
                headers = {
                    "Authorization": f"Bearer {self.services['openai']['api_key']}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.services['openai']['model'],
                    "messages": [
                        {"role": "system", "content": self._get_system_prompt(decision_type)},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200
                }
                
                response = requests.post(
                    f"{self.services['openai']['base_url']}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    decision = self._parse_ai_response(result, decision_type)
                    
                    return jsonify({
                        'success': True,
                        'decision': decision,
                        'service': 'openai',
                        'model': self.services['openai']['model']
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'OpenAI error: {response.status_code}'
                    }), response.status_code
                    
            except Exception as e:
                self.logger.error(f"Error making AI decision: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
                
        @self.app.route('/api/decision/unified', methods=['POST'])
        def unified_decision():
            """Endpoint unifié qui combine parsing et décision IA"""
            try:
                data = request.json
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                    
                image_data = data.get('image')
                context = data.get('context', {})
                decision_type = data.get('type', 'popup')
                
                # Étape 1: Parser l'image si fournie
                parsed_elements = {}
                if image_data:
                    parse_response = requests.post(
                        f"{self.services['omniparser']['url']}/parse/",
                        json={"image": image_data}
                    )
                    
                    if parse_response.status_code == 200:
                        parsed_elements = parse_response.json()
                    else:
                        self.logger.warning("Failed to parse image, continuing without parsed elements")
                        
                # Étape 2: Prendre une décision IA
                prompt = self._build_ai_prompt(context, parsed_elements, decision_type)
                
                headers = {
                    "Authorization": f"Bearer {self.services['openai']['api_key']}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.services['openai']['model'],
                    "messages": [
                        {"role": "system", "content": self._get_system_prompt(decision_type)},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 200
                }
                
                ai_response = requests.post(
                    f"{self.services['openai']['base_url']}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if ai_response.status_code == 200:
                    result = ai_response.json()
                    decision = self._parse_ai_response(result, decision_type)
                    
                    return jsonify({
                        'success': True,
                        'decision': decision,
                        'parsed_elements': parsed_elements,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'AI decision error: {ai_response.status_code}'
                    }), ai_response.status_code
                    
            except Exception as e:
                self.logger.error(f"Error in unified decision: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
                
        @self.app.route('/api/decision/health')
        def health_check():
            """Vérifie la santé de tous les services de décision"""
            health_status = {
                "unified_server": "healthy",
                "services": {}
            }
            
            # Vérifier OmniParser
            try:
                response = requests.get(
                    f"{self.services['omniparser']['url']}/health",
                    timeout=5
                )
                health_status["services"]["omniparser"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except:
                health_status["services"]["omniparser"] = {
                    "status": "unreachable"
                }
                
            # Vérifier OpenAI
            health_status["services"]["openai"] = {
                "status": "configured" if self.services['openai']['api_key'] else "not_configured"
            }
            
            overall_health = all(
                service.get("status") in ["healthy", "configured"] 
                for service in health_status["services"].values()
            )
            
            return jsonify({
                **health_status,
                "overall_health": "healthy" if overall_health else "degraded"
            }), 200 if overall_health else 503
            
    def _get_system_prompt(self, decision_type: str) -> str:
        """Return the appropriate system prompt based on decision type"""
        prompts = {
            "popup": """You are an AI assistant expert in Monopoly. 
                       Analyze game popups and make strategic decisions.
                       Always respond with JSON containing: 
                       {"action": "yes/no/buy/sell/etc", "confidence": 0-100, "reason": "explanation"}""",
            
            "property": """You are a real estate expert in Monopoly.
                          Evaluate properties and recommend strategic purchases/sales.""",
                          
            "trade": """You are an expert negotiator in Monopoly.
                       Analyze trade proposals and recommend the best options.""",
                       
            "idle_action": """You are a Monopoly game assistant helping when the game is idle.
                            Analyze the screen to determine what action the current player should take.
                            Common actions include: rolling dice, ending turn, making decisions.
                            Respond with JSON: {"action": "roll/end_turn/click_button", "target": "element to click", "reason": "why"}"""
        }
        return prompts.get(decision_type, prompts["popup"])
        
    def _build_ai_prompt(self, context: Dict, parsed_elements: Dict, decision_type: str) -> str:
        """Build the prompt for AI"""
        prompt_parts = []
        
        # Game context
        if context:
            prompt_parts.append(f"Game context: {json.dumps(context, indent=2)}")
            
        # Parsed elements
        if parsed_elements:
            prompt_parts.append(f"Detected elements: {json.dumps(parsed_elements, indent=2)}")
            
        # Specific question
        if decision_type == "popup":
            prompt_parts.append("What action do you recommend for this popup?")
        elif decision_type == "property":
            prompt_parts.append("Should I buy this property?")
        elif decision_type == "trade":
            prompt_parts.append("Is this trade advantageous?")
        elif decision_type == "idle_action":
            idle_instruction = context.get("instruction", "The game appears idle. What should the player do?")
            prompt_parts.append(idle_instruction)
            
        return "\n\n".join(prompt_parts)
        
    def _parse_ai_response(self, response: Dict, decision_type: str) -> Dict:
        """Parse la réponse de l'IA"""
        try:
            message = response['choices'][0]['message']['content']
            
            # Essayer de parser comme JSON
            try:
                return json.loads(message)
            except:
                # Si pas du JSON, créer une structure par défaut
                return {
                    "action": self._extract_action_from_text(message),
                    "confidence": 70,
                    "reason": message,
                    "raw_response": message
                }
        except Exception as e:
            self.logger.error(f"Error parsing AI response: {e}")
            return {
                "action": "no",
                "confidence": 0,
                "reason": "Error parsing response",
                "error": str(e)
            }
            
    def _extract_action_from_text(self, text: str) -> str:
        """Extrait l'action du texte de réponse"""
        text_lower = text.lower()
        
        # Mots-clés pour différentes actions
        if any(word in text_lower for word in ["oui", "yes", "accepter", "accept"]):
            return "yes"
        elif any(word in text_lower for word in ["non", "no", "refuser", "refuse"]):
            return "no"
        elif any(word in text_lower for word in ["acheter", "buy", "purchase"]):
            return "buy"
        elif any(word in text_lower for word in ["vendre", "sell"]):
            return "sell"
        else:
            return "unknown"
            
    def run(self, host='0.0.0.0', port=7000, debug=False):
        """Démarre le serveur unifié"""
        self.logger.info(f"Starting Unified Decision Server on port {port}")
        self.app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = UnifiedDecisionServer()
    server.run(debug=True)