"""Dice and movement states."""
from ...core.base import State, register_state


@register_state
class DiceRoll(State):
    name = "DiceRoll"
    def run(self, ctx):
        ctx.game.roll_dice(ctx.player_id)
        return "MoveToken"


@register_state
class MoveToken(State):
    name = "MoveToken"
    def run(self, ctx):
        ctx.game.move_player_token(ctx.player_id)
        return "LandingDecision"