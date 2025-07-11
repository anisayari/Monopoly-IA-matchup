"""
Main script to run the game with AI players.

This integrates the AI system with the existing game infrastructure.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.game.monopoly import MonopolyGame
from src.game.contexte import Contexte
from src.game.listeners import MonopolyListeners
from src.ai.ai_game_manager import AIGameManager
from config import Config


class AIEnabledMonopolyGame:
    """Monopoly game with AI integration."""
    
    def __init__(self, ai_config: Dict[str, Any]):
        """Initialize game with AI support."""
        # Initialize base game components
        self.config = Config()
        self.listeners = MonopolyListeners()
        self.contexte = Contexte()
        self.monopoly = MonopolyGame(self.listeners, self.contexte)
        
        # Initialize AI manager
        self.ai_manager = AIGameManager(self.monopoly, ai_config)
        
        # Setup display
        self._setup_display()
    
    def _setup_display(self):
        """Setup game display with AI indicators."""
        # This would integrate with the existing display system
        # For now, we'll use console output
        
        # Listen to context events for display
        self.contexte.on("*", self._on_context_event)
        
        # Listen to AI decisions
        if hasattr(self.ai_manager, 'event_listener'):
            # Could add custom display for AI decisions
            pass
    
    def _on_context_event(self, event_type: str, data: Dict[str, Any]):
        """Handle context events for display."""
        # Check if this is an AI player action
        player_id = data.get('player')
        if player_id is not None and player_id in self.ai_manager.ai_players:
            print(f"[AI Player {player_id}] {event_type}: {data.get('message', '')}")
        else:
            print(f"[Player {player_id}] {event_type}: {data.get('message', '')}")
    
    def start(self):
        """Start the game with AI."""
        print("=== Monopoly with AI Players ===")
        print(f"AI Players: {list(self.ai_manager.ai_players.keys())}")
        print("Starting game...")
        
        # Start components
        self.listeners.start()
        self.ai_manager.start()
        
        # Main game loop would go here
        # For now, just keep running
        try:
            print("\nGame is running. Press Ctrl+C to stop.")
            print("AI will automatically make decisions when it's their turn.\n")
            
            # Keep the main thread alive
            import time
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nStopping game...")
            self.stop()
    
    def stop(self):
        """Stop the game."""
        self.ai_manager.stop()
        self.listeners.stop()
        print("Game stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run Monopoly with AI players')
    parser.add_argument(
        '--ai-players', 
        type=str, 
        default='0',
        help='Comma-separated list of player IDs to be controlled by AI (e.g., "0,2")'
    )
    parser.add_argument(
        '--openai-key',
        type=str,
        default=None,
        help='OpenAI API key (or set OPENAI_API_KEY environment variable)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4-turbo-preview',
        help='OpenAI model to use'
    )
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.7,
        help='Temperature for AI decisions (0.0-1.0)'
    )
    
    args = parser.parse_args()
    
    # Parse AI players
    ai_player_ids = [int(x.strip()) for x in args.ai_players.split(',')]
    
    # Build AI configuration
    ai_config = {
        'ai_players': ai_player_ids,
        'openai_api_key': args.openai_key or os.getenv('OPENAI_API_KEY'),
        'model': args.model,
        'temperature': args.temperature
    }
    
    # Validate API key
    if not ai_config['openai_api_key']:
        print("Error: OpenAI API key is required. Set OPENAI_API_KEY or use --openai-key")
        sys.exit(1)
    
    # Create and start game
    game = AIEnabledMonopolyGame(ai_config)
    game.start()


if __name__ == '__main__':
    main()