# AI System Tests

This directory contains comprehensive tests for the AI integration system.

## Test Structure

### Unit Tests

1. **`test_game_event_listener.py`**
   - Tests event detection and decision context creation
   - Validates message parsing and pattern matching
   - Ensures proper event callbacks

2. **`test_ai_game_manager.py`**
   - Tests AI orchestration and decision making
   - Validates state synchronization
   - Tests multiple AI player management

3. **`test_action_executor.py`**
   - Tests UI element detection simulation
   - Validates action execution logic
   - Tests error handling

### Integration Tests

4. **`test_integration.py`**
   - Tests complete workflow from event to action
   - Validates component interactions
   - Tests error recovery

5. **`test_offline_simulation.py`**
   - Tests without external dependencies
   - Simulates complete game scenarios
   - Validates AI strategies

### Test Helpers

6. **`mock_helpers.py`**
   - Provides mock objects for testing
   - Game state factories
   - Event simulation utilities

## Running Tests

### Run All Tests
```bash
python tests/ai/run_all_tests.py
```

### Run Specific Test Module
```bash
python tests/ai/run_all_tests.py test_game_event_listener
```

### Run with unittest
```bash
python -m unittest tests.ai.test_game_event_listener
```

### Run with pytest (if installed)
```bash
pytest tests/ai/
```

## Test Coverage

The test suite covers:

- ✅ Event detection for all decision types
- ✅ AI decision making logic
- ✅ Action execution simulation
- ✅ State synchronization
- ✅ Error handling and recovery
- ✅ Multiple AI players
- ✅ Different AI strategies
- ✅ Complete game scenarios

## Mock Dependencies

Tests use mocks for:
- OpenAI API calls
- OmniParser service
- PyAutoGUI (no actual clicks)
- Screenshot capture
- Game memory reading

## Writing New Tests

When adding new features:

1. Add unit tests for individual components
2. Add integration tests for workflows
3. Update offline simulation tests
4. Use mock_helpers for consistent test data

Example test structure:
```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # Create mocks and fixtures
        self.game = MockMonopolyGame()
        
    def test_feature_behavior(self):
        # Test specific behavior
        result = feature_function()
        self.assertEqual(result, expected)
```

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- All interactions are mocked
- Deterministic results
- Fast execution (<10 seconds)

## Debugging Tests

To debug failing tests:

1. Run with verbose output:
   ```bash
   python -m unittest tests.ai.test_name -v
   ```

2. Add print statements in tests
3. Use debugger:
   ```python
   import pdb; pdb.set_trace()
   ```

4. Check mock call arguments:
   ```python
   mock_object.assert_called_with(expected_args)
   print(mock_object.call_args_list)
   ```