"""Rent payment states."""
from ...core.base import State, register_state


@register_state
class LD_RentBranch(State):
    name = "LD_RentBranch"
    def run(self, ctx):
        return "LD_PayRent"


@register_state
class LD_PayRent(State):
    name = "LD_PayRent"
    def run(self, ctx):
        ctx.game.pay_rent(ctx.player_id)
        return "LD_CheckCash"


@register_state
class LD_CheckCash(State):
    name = "LD_CheckCash"
    def run(self, ctx):
        if ctx.cash < 0:
            return "LD_Mortgage"
        return "LD_Done"


@register_state
class LD_Mortgage(State):
    name = "LD_Mortgage"
    def run(self, ctx):
        ctx.game.mortgage_until_positive(ctx.player_id)
        return "LD_PayAfterMort"


@register_state
class LD_PayAfterMort(State):
    name = "LD_PayAfterMort"
    def run(self, ctx):
        ctx.game.settle_negative_cash(ctx.player_id)
        return "LD_Done"