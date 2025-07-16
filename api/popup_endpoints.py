"""
API endpoints pour la gestion centralisée des popups
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from services.popup_service import PopupService
from services.event_bus import EventTypes

def create_popup_blueprint(popup_service: PopupService):
    """Crée le blueprint pour les endpoints popup"""
    
    popup_api = Blueprint('popup_api', __name__)
    
    @popup_api.route('/api/popups/detected', methods=['POST'])
    def popup_detected():
        """Endpoint appelé quand un popup est détecté par le monitor"""
        try:
            data = request.json
            
            # Valider les données
            required_fields = ['text', 'screenshot_base64']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing field: {field}'}), 400
            
            # Enregistrer le popup
            popup_id = popup_service.register_popup(data)
            
            # Analyser immédiatement avec OmniParser
            screenshot_base64 = data.get('screenshot_base64')
            if screenshot_base64:
                print(f"[POPUP] Analyzing popup {popup_id} with OmniParser...")
                analysis_result = popup_service.analyze_popup(popup_id, screenshot_base64)
                
                if analysis_result.get('success'):
                    print(f"[POPUP] Analysis complete. Found {len(analysis_result.get('options', []))} options")
                    
                    # Récupérer le contexte du jeu
                    game_context = _get_game_context()
                    
                    # Demander une décision à l'IA
                    popup_service.request_ai_decision(popup_id, game_context)
                else:
                    print(f"[POPUP] Analysis failed: {analysis_result.get('error')}")
            
            return jsonify({
                'success': True,
                'popup_id': popup_id,
                'message': 'Popup registered and being processed'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @popup_api.route('/api/popups/<popup_id>/status', methods=['GET'])
    def get_popup_status(popup_id):
        """Récupère le statut d'un popup"""
        status = popup_service.get_popup_status(popup_id)
        if status:
            return jsonify(status)
        return jsonify({'error': 'Popup not found'}), 404
    
    @popup_api.route('/api/popups/active', methods=['GET'])
    def get_active_popups():
        """Liste tous les popups actifs"""
        popups = popup_service.get_active_popups()
        return jsonify({
            'count': len(popups),
            'popups': popups
        })
    
    @popup_api.route('/api/popups/<popup_id>/execute', methods=['POST'])
    def execute_decision(popup_id):
        """Exécute manuellement une décision"""
        try:
            data = request.json
            decision = data.get('decision')
            coordinates = data.get('coordinates', (0, 0))
            
            if not decision:
                return jsonify({'error': 'Missing decision'}), 400
            
            success = popup_service.execute_decision(popup_id, decision, coordinates)
            
            if success:
                return jsonify({'success': True, 'message': 'Decision executed'})
            else:
                return jsonify({'error': 'Failed to execute decision'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @popup_api.route('/api/popups/stats', methods=['GET'])
    def get_popup_stats():
        """Récupère les statistiques des popups"""
        popups = popup_service.get_active_popups()
        
        stats = {
            'total_active': len(popups),
            'by_status': {},
            'by_type': {},
            'average_response_time': 0
        }
        
        # Calculer les stats
        response_times = []
        for popup in popups:
            # Par statut
            status = popup.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Par type
            popup_type = _extract_popup_type(popup.get('text', ''))
            stats['by_type'][popup_type] = stats['by_type'].get(popup_type, 0) + 1
            
            # Temps de réponse
            if 'detected_at' in popup and 'executed_at' in popup:
                detected = datetime.fromisoformat(popup['detected_at'])
                executed = datetime.fromisoformat(popup['executed_at'])
                response_time = (executed - detected).total_seconds()
                response_times.append(response_time)
        
        if response_times:
            stats['average_response_time'] = sum(response_times) / len(response_times)
        
        return jsonify(stats)
    
    def _get_game_context():
        """Récupère le contexte actuel du jeu"""
        import os
        import json
        
        context_file = os.path.join(os.path.dirname(__file__), '..', 'context', 'context.json')
        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _extract_popup_type(text):
        """Extrait le type de popup du texte"""
        text_lower = text.lower()
        if 'buy' in text_lower:
            return 'buy'
        elif 'roll' in text_lower:
            return 'roll'
        elif 'trade' in text_lower:
            return 'trade'
        elif 'auction' in text_lower:
            return 'auction'
        else:
            return 'other'
    
    return popup_api