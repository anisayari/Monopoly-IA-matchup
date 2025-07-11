"""Base classes for the Monopoly AI state machine."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict, Type


class AIContext:
    """Mutable state shared by all decision nodes."""

    def __init__(self, player_id: int, game):
        self.player_id = player_id        # ID of the AI player in the game engine
        self.game = game                  # Reference to the game (dependency‑injection)
        self.current_state: Optional["State"] = None  # Active State object
        # Add whatever blackboard data you need here, e.g.:
        self.cash: int = 0
        self.properties = []
        self.jail_turns: int = 0
        self.doubles_counter: int = 0


class State(ABC):
    """Abstract base‑class for every AI decision node."""

    name: str  # each subclass sets a unique *name* class attribute

    def __init__(self):
        # Pre‑allocate anything the state needs (timers, ML models, etc.)
        pass

    # ------ Life‑cycle hooks ------
    def on_enter(self, ctx: AIContext) -> None:
        """Optional: called once when the state becomes active."""
        pass

    @abstractmethod
    def run(self, ctx: AIContext) -> Optional[str]:
        """Perform the state's logic.

        Return the *name* of the next state, or ``None`` to stay in the same
        state until the next simulation step.
        """

    def on_exit(self, ctx: AIContext) -> None:
        """Optional: called once when the state is about to be left."""
        pass


# Helper decorator to register concrete states automatically ------------------
_state_registry: Dict[str, Type["State"]] = {}

def register_state(cls):
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"State class {cls.__name__} must define a non‑empty 'name' attribute")
    if cls.name in _state_registry:
        raise ValueError(f"Duplicate state name: {cls.name}")
    _state_registry[cls.name] = cls
    return cls


def get_state(name: str) -> State:
    """Factory: instantiate a state by its *name*."""
    cls = _state_registry[name]
    return cls()

state_map: Dict[str, Type[State]] = _state_registry  # exposed mapping