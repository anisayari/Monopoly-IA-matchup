"""Turn management states."""
from ...core.base import State, register_state


@register_state
class AI_Turn(State):
    """Root state – dispatches the per‑turn flow."""
    name = "AI_Turn"

    def run(self, ctx):
        return "SenseState"


@register_state
class DoubleCheck(State):
    name = "DoubleCheck"
    def run(self, ctx):
        if ctx.game.last_roll_was_doubles(ctx.player_id):
            if ctx.doubles_counter >= 2:
                ctx.doubles_counter = 0
                return "DC_Prison"
            ctx.doubles_counter += 1
            return "DiceRoll"
        ctx.doubles_counter = 0
        return "TurnEnd"


@register_state
class DC_Prison(State):
    name = "DC_Prison"
    def run(self, ctx):
        ctx.game.send_player_to_jail(ctx.player_id)
        return None  # Engine will detect prison and move to next player


@register_state
class TurnEnd(State):
    name = "TurnEnd"
    def run(self, ctx):
        ctx.game.end_turn(ctx.player_id)
        return None  # Signal end of AI turn