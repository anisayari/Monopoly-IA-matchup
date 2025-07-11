"""
AI Integration Helper - Adds AI capabilities to existing game without modifying core files.

This module provides functions to integrate AI into the existing main.py and app.py
without breaking existing functionality.
"""

import os
from typing import Optional, Dict, Any
from .ai_game_manager import AIGameManager


class AIIntegration:
    """Helper class to integrate AI into existing game infrastructure."""
    
    @staticmethod
    def enable_ai_for_game(monopoly_game, ai_config: Optional[Dict[str, Any]] = None) -> AIGameManager:
        """
        Enable AI for an existing MonopolyGame instance.
        
        Args:
            monopoly_game: The existing MonopolyGame instance
            ai_config: Optional AI configuration
            
        Returns:
            AIGameManager instance
        """
        # Default config if not provided
        if ai_config is None:
            ai_config = {
                'ai_players': [0],  # Default: Player 0 is AI
                'openai_api_key': os.getenv('OPENAI_API_KEY'),
                'model': 'gpt-4-turbo-preview',
                'temperature': 0.7
            }
        
        # Create and start AI manager
        ai_manager = AIGameManager(monopoly_game, ai_config)
        ai_manager.start()
        
        print(f"[AI Integration] AI enabled for players: {ai_config.get('ai_players', [0])}")
        
        return ai_manager
    
    @staticmethod
    def add_ai_to_main(monopoly, enable_ai: bool = False, ai_players: list = None):
        """
        Add AI to the main.py game loop.
        
        This function should be called after MonopolyGame is created in main.py.
        
        Args:
            monopoly: The MonopolyGame instance from main.py
            enable_ai: Whether to enable AI
            ai_players: List of player IDs to be controlled by AI
            
        Returns:
            AIGameManager if AI is enabled, None otherwise
        """
        if not enable_ai:
            return None
        
        ai_config = {
            'ai_players': ai_players or [0],
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
        }
        
        # Check if API key is available
        if not ai_config['openai_api_key']:
            print("[AI Integration] Warning: OPENAI_API_KEY not set. AI features disabled.")
            return None
        
        return AIIntegration.enable_ai_for_game(monopoly, ai_config)
    
    @staticmethod
    def add_ai_to_flask_app(app, monopoly):
        """
        Add AI endpoints to Flask app.
        
        This adds REST API endpoints for controlling AI players.
        
        Args:
            app: Flask app instance
            monopoly: MonopolyGame instance
        """
        ai_manager = None
        
        @app.route('/api/ai/enable', methods=['POST'])
        def enable_ai():
            """Enable AI for specified players."""
            nonlocal ai_manager
            
            data = app.get_json()
            player_ids = data.get('players', [0])
            
            if ai_manager is None:
                ai_config = {
                    'ai_players': player_ids,
                    'openai_api_key': data.get('api_key') or os.getenv('OPENAI_API_KEY'),
                    'model': data.get('model', 'gpt-4-turbo-preview'),
                    'temperature': data.get('temperature', 0.7)
                }
                
                if not ai_config['openai_api_key']:
                    return {'error': 'OpenAI API key required'}, 400
                
                ai_manager = AIIntegration.enable_ai_for_game(monopoly, ai_config)
                
            return {'status': 'AI enabled', 'players': player_ids}
        
        @app.route('/api/ai/disable', methods=['POST'])
        def disable_ai():
            """Disable AI."""
            nonlocal ai_manager
            
            if ai_manager:
                ai_manager.stop()
                ai_manager = None
            
            return {'status': 'AI disabled'}
        
        @app.route('/api/ai/status', methods=['GET'])
        def ai_status():
            """Get AI status."""
            if ai_manager:
                return {
                    'enabled': True,
                    'players': list(ai_manager.ai_players.keys()),
                    'model': ai_manager.ai_config.get('model', 'unknown')
                }
            else:
                return {'enabled': False}
        
        @app.route('/api/ai/set_player', methods=['POST'])
        def set_ai_player():
            """Enable/disable AI for a specific player."""
            if not ai_manager:
                return {'error': 'AI not enabled'}, 400
            
            data = app.get_json()
            player_id = data.get('player_id')
            enabled = data.get('enabled', True)
            
            if player_id is None:
                return {'error': 'player_id required'}, 400
            
            ai_manager.set_ai_player(player_id, enabled)
            
            return {
                'player_id': player_id,
                'ai_enabled': enabled
            }
        
        print("[AI Integration] AI endpoints added to Flask app")
        return ai_manager


# Example usage in main.py:
"""
# At the top of main.py, add:
from src.ai.ai_integration import AIIntegration

# After creating monopoly game:
monopoly = MonopolyGame(listeners, contexte)

# Add this line to enable AI:
ai_manager = AIIntegration.add_ai_to_main(
    monopoly, 
    enable_ai=True,  # Set from command line arg or config
    ai_players=[0]   # Which players should be AI
)

# At the end, stop AI manager:
if ai_manager:
    ai_manager.stop()
"""

# Example usage in app.py:
"""
# At the top of app.py, add:
from src.ai.ai_integration import AIIntegration

# After creating monopoly game:
monopoly = MonopolyGame(listeners, contexte)

# Add AI endpoints:
ai_manager = AIIntegration.add_ai_to_flask_app(app, monopoly)
"""