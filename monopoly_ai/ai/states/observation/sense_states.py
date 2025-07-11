"""Observation and sensing states."""
from ...core.base import State, register_state


@register_state
class SenseState(State):
    name = "SenseState"
    def run(self, ctx):
        # Gather game data (board, opponents, cash, etc.)
        return "JailCheck"


@register_state
class JailCheck(State):
    name = "JailCheck"
    def run(self, ctx):
        return "JailDecision" if ctx.game.is_in_jail(ctx.player_id) else "DiceRoll"