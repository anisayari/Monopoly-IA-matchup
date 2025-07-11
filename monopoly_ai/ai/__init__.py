"""Monopoly AI module."""
from .core.base import AIContext, State, get_state, state_map
from . import states  # This imports all states and registers them

# Import OpenAI components if needed
try:
    from .openai_agent import OpenAIMonopolyAgent
    from .game_manager import MonopolyGameManager
    __all__ = ['AIContext', 'State', 'get_state', 'state_map', 'OpenAIMonopolyAgent', 'MonopolyGameManager']
except ImportError:
    # OpenAI not available
    __all__ = ['AIContext', 'State', 'get_state', 'state_map']