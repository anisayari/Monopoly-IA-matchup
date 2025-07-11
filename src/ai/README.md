# AI Integration Module

This module provides AI capabilities for the Monopoly game, allowing AI players to make decisions automatically.

## Architecture Overview

The AI system is divided into three main components:

### 1. GameEventListener (`game_event_listener.py`)
- Listens to game events from the real game (Dolphin emulator)
- Detects when decisions are needed (buy property, jail strategy, etc.)
- Translates game messages into decision contexts

### 2. AIGameManager (`ai_game_manager.py`)
- Central orchestrator between real game and AI
- Maintains synchronization between real and simulated game states
- Requests decisions from the monopoly_ai system
- Manages AI players and their agents

### 3. ActionExecutor (`action_executor.py`)
- Executes AI decisions in the real game
- Uses OmniParser to identify UI elements
- Performs clicks and keyboard inputs via pyautogui

## Setup

### Prerequisites

1. **OmniParser Service**: Must be running at `http://localhost:8000`
   ```bash
   cd omniparserserver
   docker-compose up
   ```

2. **OpenAI API Key**: Set in environment or pass via config
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. **Python Dependencies**: Install required packages
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Method 1: Standalone AI Mode

Run the game with AI players:

```bash
python src/ai/run_ai_mode.py --ai-players 0,2 --model gpt-4-turbo-preview
```

Options:
- `--ai-players`: Comma-separated list of player IDs to be AI-controlled (default: "0")
- `--openai-key`: OpenAI API key (or use OPENAI_API_KEY env var)
- `--model`: OpenAI model to use (default: "gpt-4-turbo-preview")
- `--temperature`: AI decision temperature 0.0-1.0 (default: 0.7)

### Method 2: Integration with Existing Game

#### In main.py (Console Mode)

```python
from src.ai.ai_integration import AIIntegration

# After creating monopoly game
monopoly = MonopolyGame(listeners, contexte)

# Enable AI for player 0
ai_manager = AIIntegration.add_ai_to_main(
    monopoly, 
    enable_ai=True,
    ai_players=[0]
)

# Remember to stop when done
if ai_manager:
    ai_manager.stop()
```

#### In app.py (Web Mode)

```python
from src.ai.ai_integration import AIIntegration

# After creating monopoly game
monopoly = MonopolyGame(listeners, contexte)

# Add AI REST endpoints
ai_manager = AIIntegration.add_ai_to_flask_app(app, monopoly)
```

This adds the following endpoints:
- `POST /api/ai/enable` - Enable AI for specified players
- `POST /api/ai/disable` - Disable AI
- `GET /api/ai/status` - Get current AI status
- `POST /api/ai/set_player` - Enable/disable AI for specific player

## How It Works

1. **Event Detection**: GameEventListener monitors game messages and events
2. **Decision Request**: When a decision is needed, it's added to the queue
3. **State Sync**: AIGameManager synchronizes real game state with simulation
4. **AI Decision**: The AI agent (from monopoly_ai) makes a decision
5. **Action Execution**: ActionExecutor uses OmniParser to find and click UI elements

## Decision Types Supported

- **Buy Property**: Decide whether to purchase available properties
- **Jail Strategy**: Choose between using card, paying fine, or rolling
- **Build Houses**: Decide when and where to build houses/hotels
- **Auction Bidding**: Participate in property auctions
- **Mortgage Decisions**: Manage property mortgages when low on cash
- **Trade Responses**: Accept or decline trade offers (basic support)

## Configuration

Create an AI configuration dictionary:

```python
ai_config = {
    'ai_players': [0, 2],  # Player IDs to be AI-controlled
    'openai_api_key': 'your_key_here',
    'model': 'gpt-4-turbo-preview',
    'temperature': 0.7,  # 0.0 = deterministic, 1.0 = creative
}
```

## Troubleshooting

### OmniParser Connection Failed
- Ensure OmniParser service is running: `docker-compose up` in omniparserserver/
- Check if accessible at http://localhost:8000

### AI Not Making Decisions
- Check if OPENAI_API_KEY is set correctly
- Verify player IDs match actual game players
- Check console for error messages

### Actions Not Executing
- Ensure game window is visible and not minimized
- Check if pyautogui can access the screen (security permissions)
- Verify OmniParser is detecting UI elements correctly

## Extending the AI

To add new decision types:

1. Add new DecisionType in `game_event_listener.py`
2. Add detection pattern in `decision_patterns`
3. Implement decision logic in `ai_game_manager.py`
4. Add execution logic in `action_executor.py`

## Performance Considerations

- AI decisions typically take 1-3 seconds
- State synchronization happens every second
- Screenshot caching reduces OmniParser calls
- Multiple AI players can play simultaneously

## Limitations

- Requires OmniParser for UI element detection
- Trade negotiations are basic (accept/decline only)
- Complex UI interactions may fail if layout changes
- Requires stable internet for OpenAI API calls