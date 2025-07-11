"""Jail-related states."""
from ...core.base import State, register_state


@register_state
class JailDecision(State):
    name = "JailDecision"
    def run(self, ctx):
        return "EvaluateReleaseOptions"


@register_state
class EvaluateReleaseOptions(State):
    name = "EvaluateReleaseOptions"
    def run(self, ctx):
        # Choose card, pay, or roll – placeholder policy
        if ctx.game.has_get_out_card(ctx.player_id):
            return "JD_UseCard"
        elif ctx.cash >= 50:
            return "JD_PayBail"
        else:
            return "JD_Roll"


@register_state
class JD_UseCard(State):
    name = "JD_UseCard"
    def run(self, ctx):
        ctx.game.use_get_out_card(ctx.player_id)
        return "JD_Released"


@register_state
class JD_PayBail(State):
    name = "JD_PayBail"
    def run(self, ctx):
        ctx.game.pay_bail(ctx.player_id)
        return "JD_Released"


@register_state
class JD_Roll(State):
    name = "JD_Roll"
    def run(self, ctx):
        doubles = ctx.game.roll_for_doubles(ctx.player_id)
        return "JD_Released" if doubles else "JD_EndTurn"


@register_state
class JD_Released(State):
    name = "JD_Released"
    def run(self, ctx):
        return "DiceRoll"


@register_state
class JD_EndTurn(State):
    name = "JD_EndTurn"
    def run(self, ctx):
        return None  # stay here -> turn complete in the engine