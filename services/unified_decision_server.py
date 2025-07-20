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
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ai_service import get_ai_service

class UnifiedDecisionServer:
    """Serveur unifié pour gérer toutes les décisions tierces"""
    
    def __init__(self, app: Flask = None):
        self.app = app or Flask(__name__)
        self.logger = logging.getLogger(__name__)
        self.game_settings = self._load_game_settings()
        
        # Configuration des services
        self.services = {
            "omniparser": {
                "url": "http://localhost:8000",
                "endpoints": {
                    "parse": "/parse/",
                    "health": "/health"
                }
            }
        }
        
        # Initialiser le service AI
        self.ai_service = get_ai_service()
        
        self.setup_routes()
        
    def _load_game_settings(self):
        """Charge les paramètres du jeu depuis settings.json"""
        settings_path = os.path.join("config", "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur chargement settings: {e}")
        return {}
        
    def setup_routes(self):
        """Configure les routes du serveur unifié"""
        
        @self.app.route('/api/decision/parse', methods=['POST'])
        def parse_image():
            """Parse une image avec OmniParser"""
            try:
                data = request.json
                if not data or 'image' not in data:
                    return jsonify({'error': 'No image provided'}), 400
                
                # Appeler OmniParser
                omniparser_url = f"{self.services['omniparser']['url']}{self.services['omniparser']['endpoints']['parse']}"
                response = requests.post(
                    omniparser_url,
                    json={'base64_image': data['image']},
                    timeout=30
                )
                
                if response.status_code == 200:
                    return jsonify({
                        'success': True,
                        'data': response.json()
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'OmniParser error: {response.status_code}'
                    }), response.status_code
                    
            except Exception as e:
                self.logger.error(f"Error parsing image: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/decide', methods=['POST'])
        def decide():
            """Endpoint unique pour les décisions IA"""
            try:
                data = request.json
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                # Extraire les données
                popup_text = data.get('popup_text', '')
                options = data.get('options', [])
                game_context = data.get('game_context', {})
                keywords = data.get('keywords', [])
                all_detected_icons = data.get('all_detected_icons', [])
                
                # Utiliser le service AI pour prendre la décision
                result = self.ai_service.make_decision(
                    popup_text=popup_text,
                    options=options,
                    game_context=game_context
                )
                
                # Retourner la réponse formatée
                return jsonify({
                    'success': True,
                    'decision': result['decision'],
                    'reason': result['reason'],
                    'confidence': result['confidence']
                })
                    
            except Exception as e:
                self.logger.error(f"Error making decision: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/decision/health', methods=['GET'])
        def health_check():
            """Vérifie l'état des services"""
            try:
                services_status = {}
                
                # Vérifier OmniParser
                try:
                    omni_response = requests.get(
                        f"{self.services['omniparser']['url']}{self.services['omniparser']['endpoints']['health']}",
                        timeout=2
                    )
                    services_status['omniparser'] = omni_response.status_code == 200
                except:
                    services_status['omniparser'] = False
                
                # Vérifier AI Service
                services_status['ai_service'] = self.ai_service.available
                
                return jsonify({
                    'success': True,
                    'services': services_status
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    
    
    def run(self, host='0.0.0.0', port=7000):
        """Lance le serveur"""
        self.logger.info(f"Starting Unified Decision Server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False)

# Point d'entrée pour lancer le serveur
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    server = UnifiedDecisionServer()
    server.run()