"""Landing decision states."""
from ...core.base import State, register_state


@register_state
class LandingDecision(State):
    name = "LandingDecision"
    def run(self, ctx):
        # Examine the square type and branch
        square = ctx.game.current_square(ctx.player_id)
        if square.is_property():
            return "LD_PropertyCheck"
        elif square.is_tax():
            return "LD_TaxBranch"
        elif square.is_special():
            return "LD_Special"
        else:
            return "LD_Owned"  # default safety


@register_state
class LD_PropertyCheck(State):
    name = "LD_PropertyCheck"
    def run(self, ctx):
        prop = ctx.game.current_square(ctx.player_id)
        if prop.owner is None:
            return "LD_BuyBranch"
        elif prop.owner == ctx.player_id:
            return "LD_Owned"
        else:
            return "LD_RentBranch"


@register_state
class LD_Owned(State):
    name = "LD_Owned"
    def run(self, ctx):
        return "LD_Done"


@register_state
class LD_Special(State):
    name = "LD_Special"
    def run(self, ctx):
        ctx.game.execute_special_square(ctx.player_id)
        return "LD_Done"


@register_state
class LD_TaxBranch(State):
    name = "LD_TaxBranch"
    def run(self, ctx):
        ctx.game.pay_tax(ctx.player_id)
        return "LD_Done"


@register_state
class LD_HandleTax(State):
    name = "LD_HandleTax"
    def run(self, ctx):
        return "LD_Done"  # placeholder


@register_state
class LD_Done(State):
    name = "LD_Done"
    def run(self, ctx):
        return "LD_Exit"


@register_state
class LD_Exit(State):
    name = "LD_Exit"
    def run(self, ctx):
        return "PostTurnManagement"