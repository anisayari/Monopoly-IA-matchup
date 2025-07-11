"""Property buying states."""
from ...core.base import State, register_state


@register_state
class LD_BuyBranch(State):
    name = "LD_BuyBranch"
    def run(self, ctx):
        return "LD_EvalLiquidity"


@register_state
class LD_EvalLiquidity(State):
    name = "LD_EvalLiquidity"
    def run(self, ctx):
        price = ctx.game.current_square(ctx.player_id).price
        if ctx.cash >= price and ctx.game.estimate_roi(ctx.player_id, price) > 0:
            return "LD_Purchase"
        return "LD_Auction"


@register_state
class LD_Purchase(State):
    name = "LD_Purchase"
    def run(self, ctx):
        ctx.game.buy_property(ctx.player_id)
        return "LD_Done"


@register_state
class LD_Auction(State):
    name = "LD_Auction"
    def run(self, ctx):
        ctx.game.start_auction()
        return "LD_Done"