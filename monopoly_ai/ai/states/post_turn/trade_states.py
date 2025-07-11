"""Trading states."""
from ...core.base import State, register_state


@register_state
class PTM_TradeBranch(State):
    name = "PTM_TradeBranch"
    def run(self, ctx):
        return "PTM_FindPartner"


@register_state
class PTM_FindPartner(State):
    name = "PTM_FindPartner"
    def run(self, ctx):
        partner = ctx.game.find_best_trade_partner(ctx.player_id)
        ctx.trade_partner = partner
        return "PTM_MakeOffer" if partner is not None else "PTM_NoTrade"


@register_state
class PTM_MakeOffer(State):
    name = "PTM_MakeOffer"
    def run(self, ctx):
        ctx.game.propose_trade(ctx.player_id, ctx.trade_partner)
        return "PTM_Wait"


@register_state
class PTM_Wait(State):
    name = "PTM_Wait"
    def run(self, ctx):
        outcome = ctx.game.poll_trade_response()
        return "PTM_Accepted" if outcome == "accepted" else "PTM_Rejected"


@register_state
class PTM_Accepted(State):
    name = "PTM_Accepted"
    def run(self, ctx):
        ctx.game.finalize_trade(ctx.player_id)
        return "PTM_UpdateHold"


@register_state
class PTM_Rejected(State):
    name = "PTM_Rejected"
    def run(self, ctx):
        return "PTM_TradeEnd"


@register_state
class PTM_UpdateHold(State):
    name = "PTM_UpdateHold"
    def run(self, ctx):
        ctx.game.update_holdings(ctx.player_id)
        return "PTM_TradeEnd"


@register_state
class PTM_NoTrade(State):
    name = "PTM_NoTrade"
    def run(self, ctx):
        return "PTM_TradeEnd"


@register_state
class PTM_TradeEnd(State):
    name = "PTM_TradeEnd"
    def run(self, ctx):
        return "PTM_ImprovementCheck"