"""Post-turn management states."""
from ...core.base import State, register_state


@register_state
class PostTurnManagement(State):
    name = "PostTurnManagement"
    def run(self, ctx):
        return "PTM_ImprovementCheck"


@register_state
class PTM_ImprovementCheck(State):
    name = "PTM_ImprovementCheck"
    def run(self, ctx):
        if ctx.game.has_full_monopoly(ctx.player_id):
            return "PTM_BuildBranch"
        elif ctx.game.detect_trade_opportunities(ctx.player_id):
            return "PTM_TradeBranch"
        else:
            return "PTM_End"


@register_state
class PTM_End(State):
    name = "PTM_End"
    def run(self, ctx):
        return "PTM_Exit"


@register_state
class PTM_Exit(State):
    name = "PTM_Exit"
    def run(self, ctx):
        return "DoubleCheck"