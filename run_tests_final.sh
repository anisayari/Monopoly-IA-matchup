#!/bin/bash

# Final test runner for Monopoly AI Integration
# This version handles all the dependency issues and runs tests properly

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# Project setup
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Print header
echo -e "${BOLD}🎮 Monopoly AI Integration - Test Suite 🎮${NC}"
echo "=========================================="
echo "Project root: $PROJECT_ROOT"
echo

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Check Python
if command -v python3 &> /dev/null; then
    print_color "$GREEN" "✓ Python 3 found: $(python3 --version)"
else
    print_color "$RED" "✗ Python 3 not found"
    exit 1
fi

# Options
case "${1:-all}" in
    minimal)
        print_color "$BLUE" "\n=== Running Minimal Tests ==="
        python3 test_ai_minimal.py
        exit $?
        ;;
        
    isolated)
        print_color "$BLUE" "\n=== Running Isolated AI Tests ==="
        python3 run_ai_tests.py
        exit $?
        ;;
        
    quick)
        print_color "$BLUE" "\n=== Running Quick Component Tests ==="
        # Run just the basic component tests
        python3 -c "
import sys
import os
sys.path.insert(0, '.')

# Mock dependencies
sys.modules['dolphin_memory_engine'] = __import__('unittest.mock').mock.MagicMock()
sys.modules['win32api'] = __import__('unittest.mock').mock.MagicMock()
sys.modules['pyautogui'] = __import__('unittest.mock').mock.MagicMock()
sys.modules['mss'] = __import__('unittest.mock').mock.MagicMock()

# Test imports
try:
    from src.ai.game_event_listener import DecisionType, DecisionContext
    from src.ai.action_executor import UIElement
    print('✓ All AI modules imported successfully')
    
    # Quick functionality test
    context = DecisionContext(
        decision_type=DecisionType.BUY_PROPERTY,
        player_id=0
    )
    print(f'✓ Created decision context: {context.decision_type.value}')
    
    element = UIElement('Test', 0.9, (0,0,100,100), (50,50))
    print(f'✓ Created UI element: {element.label}')
    
    print('\\n✅ Quick tests passed!')
    
except Exception as e:
    print(f'✗ Quick test failed: {e}')
    sys.exit(1)
"
        exit $?
        ;;
        
    help)
        echo "Usage: $0 [option]"
        echo "Options:"
        echo "  all      - Run all tests (default)"
        echo "  minimal  - Run minimal test suite"
        echo "  isolated - Run isolated AI tests with full mocking"
        echo "  quick    - Run quick import and basic functionality tests"
        echo "  help     - Show this help"
        exit 0
        ;;
        
    all|*)
        # Run all test options in sequence
        print_color "$BLUE" "\n=== Running Complete Test Suite ==="
        
        # 1. Quick tests
        print_color "$YELLOW" "\n1. Quick Import Tests"
        $0 quick
        QUICK_RESULT=$?
        
        # 2. Minimal tests
        print_color "$YELLOW" "\n2. Minimal Component Tests"
        $0 minimal
        MINIMAL_RESULT=$?
        
        # Summary
        echo
        print_color "$BLUE" "======================================"
        print_color "$BLUE" "Test Summary"
        print_color "$BLUE" "======================================"
        
        if [ $QUICK_RESULT -eq 0 ]; then
            print_color "$GREEN" "✓ Quick tests: PASSED"
        else
            print_color "$RED" "✗ Quick tests: FAILED"
        fi
        
        if [ $MINIMAL_RESULT -eq 0 ]; then
            print_color "$GREEN" "✓ Minimal tests: PASSED"
        else
            print_color "$RED" "✗ Minimal tests: FAILED"
        fi
        
        # Overall result
        if [ $QUICK_RESULT -eq 0 ] && [ $MINIMAL_RESULT -eq 0 ]; then
            print_color "$GREEN" "\n✅ All tests passed!"
            exit 0
        else
            print_color "$RED" "\n❌ Some tests failed"
            exit 1
        fi
        ;;
esac