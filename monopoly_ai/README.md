# Monopoly AI

A state-machine based AI for playing Monopoly, implemented in Python.

## Project Structure

```
monopoly_ai/
├── ai/                     # AI implementation
│   ├── core/              # Base classes and utilities
│   │   └── base.py        # State, AIContext, and registry
│   └── states/            # State implementations
│       ├── observation/   # Sensing and jail check states
│       ├── jail/         # Jail-related decisions
│       ├── movement/     # Dice rolling and movement
│       ├── landing/      # Property landing decisions
│       ├── post_turn/    # Building and trading
│       └── turn_management/ # Turn flow control
├── game/                  # Game engine implementation
│   ├── board.py          # Board and property definitions
│   ├── player.py         # Player class
│   └── monopoly.py       # Main game engine
├── utils/                 # Utilities
│   └── colors.py         # Terminal color formatting
├── openai_battle.py      # Main AI battle mode
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Design

The AI uses a state machine pattern where each decision point is a separate state class. States are organized by their function:

- **Observation**: Gather game information
- **Jail**: Handle jail scenarios
- **Movement**: Dice rolls and token movement
- **Landing**: Handle landing on different square types (buy, rent, tax)
- **Post-turn**: Building improvements and trading
- **Turn Management**: Overall turn flow and doubles handling

## Installation

```bash
cd monopoly_ai
pip install -r requirements.txt

# For OpenAI battle mode:
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### OpenAI Battle Mode

First, set up your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

Then run the battle:
```bash
python openai_battle.py [num_turns] [delay_seconds]
```

Watch two OpenAI-powered AIs compete with:
- Function calling for strategic decisions
- Real-time chat between AIs
- Complete game history tracking
- Decision explanations
- Game history export to JSON
- **NEW: Colorful terminal output for better visibility**

Example:
```bash
# Run AI battle (100 turns, 1.5s delay between turns)
python openai_battle.py 100 1.5

# Quick battle (50 turns, faster)
python openai_battle.py 50 0.5
```

## How the AI Works

### Basic AI (State Machine)
The basic AI uses simple heuristics:
1. **Property Purchase**: Buy if enough cash buffer remains (>$500)
2. **Jail Strategy**: Use card first, then pay bail, finally try rolling
3. **Building**: Build when holding a monopoly and cash > $1000
4. **Rent Payment**: Mortgage properties if needed to pay rent

### OpenAI-Powered AI
The advanced AI uses GPT-4 with function calling to:
1. **Analyze game state**: Consider all players' positions, properties, and cash
2. **Strategic decisions**: Make context-aware choices based on game history
3. **Negotiation**: Chat with opponents during the game
4. **Adaptive strategy**: Learn from previous decisions and outcomes

## State Machine Flow

1. **AI_Turn** → **SenseState** → **JailCheck**
2. If in jail: → **JailDecision** → release options
3. If not: → **DiceRoll** → **MoveToken** → **LandingDecision**
4. Landing branches based on square type:
   - Property: Check ownership → Buy/Pay Rent/Skip
   - Tax: Pay tax amount
   - Special: Execute special square effect
5. **PostTurnManagement** for building/trading
6. **DoubleCheck** for handling doubles
7. **TurnEnd** to complete the turn

## Documentation

- **[STATES_GUIDE.md](STATES_GUIDE.md)** - Detailed guide of all states and decisions
- **[STATE_DIAGRAM.md](STATE_DIAGRAM.md)** - Visual flow diagram of the state machine
- **[DECISION_REFERENCE.md](DECISION_REFERENCE.md)** - Quick reference for AI decisions
- **[COLOR_GUIDE.md](COLOR_GUIDE.md)** - Terminal color coding system

## Extending the AI

To improve the AI's strategy:

1. Enhance `estimate_roi()` in game engine with better property valuation
2. Implement trading logic in `find_best_trade_partner()`
3. Add machine learning for decision making
4. Implement auction bidding strategies
5. Add opponent modeling and prediction

### Adding New Decision States

To add OpenAI-powered decisions to new states:

1. Create a new state class inheriting from `State` and `OpenAIStateMixin`
2. Override the `run()` method to call `make_decision()`
3. Define appropriate function schemas in `OpenAIMonopolyAgent`
4. Register the state with `@register_state`

Example:
```python
@register_state
class OpenAI_NewDecision(State, OpenAIStateMixin):
    name = "NewDecision"
    
    def run(self, ctx: AIContext) -> Optional[str]:
        agent = self.get_agent(ctx)
        game_state = self.get_game_state(ctx)
        decision = agent.make_decision(game_state, "decision_type", options)
        return "NextState"
```