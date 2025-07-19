"""
API endpoints pour la gestion centralisée des popups
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import requests

def create_popup_blueprint(omniparser_url="http://localhost:8000", ai_decision_url="http://localhost:7000"):
    """Crée le blueprint pour les endpoints popup"""
    
    popup_api = Blueprint('popup_api', __name__)
    
    @popup_api.route('/api/popups/analyze', methods=['POST'])
    def analyze_popup():
        """Endpoint pour analyser un screenshot avec OmniParser"""
        try:
            data = request.json
            
            # Valider les données
            if 'screenshot_base64' not in data:
                return jsonify({'error': 'Missing field: screenshot_base64'}), 400
            
            # Appeler OmniParser
            print(f"[POPUP] Analyse du screenshot avec OmniParser à {omniparser_url}...")
            try:
                omniparser_response = requests.post(
                    f"{omniparser_url}/parse/",
                    json={"base64_image": data['screenshot_base64']},
                    timeout=30
                )
            except requests.exceptions.RequestException as e:
                print(f"[POPUP] Erreur connexion OmniParser: {e}")
                return jsonify({'error': f'OmniParser connection error: {str(e)}'}), 503
            
            if not omniparser_response.ok:
                return jsonify({'error': f'OmniParser error: {omniparser_response.status_code}'}), 500
            
            omniparser_result = omniparser_response.json()
            parsed_content = omniparser_result.get('parsed_content_list', [])
            
            # Extraire les options (boutons)
            options = []
            text_content = []
            
            for item in parsed_content:
                if item.get('type') == 'text':
                    text = item.get('content', '').lower()
                    text_content.append(item.get('content', ''))
                    
                    # Détecter les boutons Monopoly
                    button_keywords = [
                        'ok', 'cancel', 'yes', 'no', 'confirm', 'accept', 'decline', 'pay',
                        'accounts', 'next turn', 'roll again', 'auction', 'buy', 'back', 
                        'trade', 'pay bail', 'roll dice', 'use card', 'bid', 'deal', 
                        'no deal', 'propose', 'request cash', 'add cash', 'mortgage',
                        'buy 1', 'buy set', 'sell 1', 'sell set', 'done'
                    ]
                    
                    if any(keyword in text for keyword in button_keywords):
                        options.append({
                            'name': text,
                            'original_text': item.get('content', ''),
                            'bbox': item.get('bbox', []),
                            'confidence': item.get('confidence', 1.0),
                            'type': 'button'
                        })
                
                elif item.get('type') == 'icon':
                    options.append({
                        'name': item['content'].lower(),
                        'bbox': item.get('bbox', []),
                        'confidence': item.get('confidence', 1.0),
                        'type': 'icon'
                    })
            
            print(f"[POPUP] Options trouvées: {[opt['name'] for opt in options]}")
            
            # Retourner l'analyse
            return jsonify({
                'success': True,
                'options': options,
                'text_content': text_content,
                'raw_parsed_content': parsed_content
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    
    @popup_api.route('/api/popups/active', methods=['GET'])
    def get_active_popups():
        """Liste tous les popups actifs"""
        # Sans popup service, retourner une liste vide
        return jsonify({
            'count': 0,
            'popups': []
        })
    
    @popup_api.route('/api/popups/stats', methods=['GET'])
    def get_popup_stats():
        """Récupère les statistiques des popups"""
        # Sans popup service, retourner des stats vides
        return jsonify({
            'total_active': 0,
            'by_status': {},
            'by_type': {},
            'average_response_time': 0
        })
    
    return popup_api