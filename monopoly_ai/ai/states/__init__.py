"""Import all state modules to register them."""
from . import observation
from . import jail
from . import movement
from . import landing
from . import post_turn
from . import turn_management

# Import specific states
from .observation.sense_states import *
from .jail.jail_states import *
from .movement.dice_states import *
from .landing.landing_states import *
from .landing.buy_states import *
from .landing.rent_states import *
from .post_turn.post_turn_states import *
from .post_turn.build_states import *
from .post_turn.trade_states import *
from .turn_management.turn_states import *