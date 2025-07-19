# Game Settings Propagation Implementation

## Overview
The game settings (player names and AI models) are now properly propagated throughout the system when configured in the dashboard.

## Key Changes

### 1. Game Settings Storage
- **File**: `/config/game_settings.json`
- Stores player names and AI model configurations
- Updated via the dashboard Game Setup modal

### 2. AI Service Updates
- **File**: `/services/ai_service.py`
- Loads game settings on initialization
- Subscribes to `game_settings.updated` events
- Dynamically selects the AI model based on the current player
- Methods added:
  - `_load_game_settings()`: Loads settings from JSON file
  - `_get_current_player_from_context()`: Determines active player
  - `_get_model_for_player()`: Returns the configured model for a player

### 3. Game Context Updates
- **File**: `/src/game/contexte.py`
- Loads game settings to use configured player names
- Updates player information with:
  - Configured names instead of default names
  - Player keys (player1, player2) for consistent identification
  - Current player tracking in global context

### 4. Unified Decision Server
- **File**: `/services/unified_decision_server.py`
- Loads game settings for default model configuration
- Uses the configured default model for AI decisions

## How It Works

1. **Settings Configuration**:
   - User opens Game Setup modal in dashboard
   - Configures player names and AI models
   - Settings saved to `/config/game_settings.json`
   - EventBus publishes `game_settings.updated` event

2. **Settings Propagation**:
   - AI Service receives the event and reloads settings
   - Game Context uses settings to display configured player names
   - Player information in context uses `player1`, `player2` keys with configured names

3. **AI Decision Making**:
   - When a popup requires a decision, AI Service:
     - Identifies the current player from game context
     - Loads the configured AI model for that player
     - Makes the API call with the player-specific model

4. **Display**:
   - Dashboard shows configured player names
   - AI Actions terminal displays configured names
   - All game events use the configured names

## Testing

To verify the propagation works:

1. Configure player names in the Game Setup modal
2. Start Dolphin and begin a game
3. Check that:
   - Player names appear correctly in the dashboard
   - AI decisions use the configured model (check logs)
   - Game context shows proper player identification

## Notes

- The system maintains backward compatibility with default names
- Player identification uses keys (player1, player2) internally
- Display names come from the configuration
- Each player can have a different AI model (future expansion)