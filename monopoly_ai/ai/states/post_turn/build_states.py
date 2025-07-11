"""Building improvement states."""
from ...core.base import State, register_state


@register_state
class PTM_BuildBranch(State):
    name = "PTM_BuildBranch"
    def run(self, ctx):
        return "PTM_EvalROI"


@register_state
class PTM_EvalROI(State):
    name = "PTM_EvalROI"
    def run(self, ctx):
        if ctx.game.evaluate_build_roi(ctx.player_id):
            return "PTM_Build"
        return "PTM_Skip"


@register_state
class PTM_Build(State):
    name = "PTM_Build"
    def run(self, ctx):
        ctx.game.build_houses_or_hotels(ctx.player_id)
        return "PTM_BuildEnd"


@register_state
class PTM_Skip(State):
    name = "PTM_Skip"
    def run(self, ctx):
        return "PTM_BuildEnd"


@register_state
class PTM_BuildEnd(State):
    name = "PTM_BuildEnd"
    def run(self, ctx):
        return "PTM_ImprovementCheck"