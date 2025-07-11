#!/bin/bash

# Monopoly AI - Complete Launch Script
# This script handles the entire launch sequence for the AI-enabled Monopoly game

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OMNIPARSER_DIR="$PROJECT_ROOT/omniparserserver"
DOLPHIN_RUNNING=false
OMNIPARSER_RUNNING=false
API_KEY_SET=false

# Print header
echo -e "${BOLD}${PURPLE}🎮 Monopoly AI - Complete Launch System 🎮${NC}"
echo "=========================================="
echo -e "${BLUE}Project: $PROJECT_ROOT${NC}"
echo

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to check if a process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to cleanup on exit
cleanup() {
    echo
    print_color "$YELLOW" "\n🧹 Cleaning up..."
    
    # Stop OmniParser if we started it
    if [ "$OMNIPARSER_PID" != "" ]; then
        print_color "$YELLOW" "Stopping OmniParser..."
        kill $OMNIPARSER_PID 2>/dev/null
        cd "$OMNIPARSER_DIR" && docker-compose down 2>/dev/null
    fi
    
    print_color "$GREEN" "✓ Cleanup complete"
    exit 0
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Step 1: Check prerequisites
print_color "$BLUE" "📋 Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    print_color "$GREEN" "✓ Python 3 found: $(python3 --version)"
else
    print_color "$RED" "✗ Python 3 not found. Please install Python 3."
    exit 1
fi

# Check Docker (for OmniParser)
if command -v docker &> /dev/null; then
    print_color "$GREEN" "✓ Docker found"
else
    print_color "$YELLOW" "⚠ Docker not found. OmniParser won't work without Docker."
fi

# Check OpenAI API key
if [ ! -z "$OPENAI_API_KEY" ]; then
    print_color "$GREEN" "✓ OpenAI API key is set"
    API_KEY_SET=true
else
    print_color "$YELLOW" "⚠ OpenAI API key not set"
    echo -n "Enter your OpenAI API key (or press Enter to skip AI): "
    read -s api_key
    echo
    if [ ! -z "$api_key" ]; then
        export OPENAI_API_KEY="$api_key"
        API_KEY_SET=true
        print_color "$GREEN" "✓ API key set for this session"
    else
        print_color "$YELLOW" "⚠ Continuing without AI features"
    fi
fi

# Check Dolphin
if check_process "Dolphin"; then
    print_color "$GREEN" "✓ Dolphin is already running"
    DOLPHIN_RUNNING=true
else
    print_color "$YELLOW" "⚠ Dolphin is not running"
    
    # Try to find Dolphin executable
    if [ -f "config.py" ]; then
        DOLPHIN_PATH=$(grep "DOLPHIN_PATH" config.py | cut -d'"' -f2)
        if [ -f "$DOLPHIN_PATH" ]; then
            echo -n "Start Dolphin? (y/n): "
            read start_dolphin
            if [ "$start_dolphin" = "y" ]; then
                print_color "$BLUE" "Starting Dolphin..."
                "$DOLPHIN_PATH" &
                sleep 5
                DOLPHIN_RUNNING=true
            fi
        fi
    fi
fi

# Step 2: Start OmniParser (if AI mode and Docker available)
if [ "$API_KEY_SET" = true ] && command -v docker &> /dev/null; then
    print_color "$BLUE" "\n🤖 Setting up OmniParser for AI..."
    
    # Check if OmniParser is already running
    if check_port 8000; then
        print_color "$GREEN" "✓ OmniParser is already running on port 8000"
        OMNIPARSER_RUNNING=true
    else
        if [ -d "$OMNIPARSER_DIR" ]; then
            print_color "$BLUE" "Starting OmniParser..."
            cd "$OMNIPARSER_DIR"
            
            # Start in background
            docker-compose up -d
            
            # Wait for it to be ready
            print_color "$YELLOW" "Waiting for OmniParser to start..."
            for i in {1..30}; do
                if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                    print_color "$GREEN" "✓ OmniParser is ready!"
                    OMNIPARSER_RUNNING=true
                    break
                fi
                echo -n "."
                sleep 1
            done
            
            if [ "$OMNIPARSER_RUNNING" = false ]; then
                print_color "$RED" "✗ OmniParser failed to start"
                print_color "$YELLOW" "Continuing without automatic clicks..."
            fi
            
            cd "$PROJECT_ROOT"
        else
            print_color "$YELLOW" "⚠ OmniParser directory not found"
        fi
    fi
fi

# Step 3: Choose launch mode
print_color "$BLUE" "\n🎯 Choose launch mode:"
echo "1) Console mode (no AI)"
echo "2) Web interface"
echo "3) AI mode - Single player"
echo "4) AI mode - Multiple players"
echo "5) Run tests"
echo "6) Exit"

echo -n "Your choice (1-6): "
read choice

case $choice in
    1)
        # Console mode
        print_color "$BLUE" "\n🎮 Launching console mode..."
        python3 main.py
        ;;
        
    2)
        # Web interface
        print_color "$BLUE" "\n🌐 Launching web interface..."
        print_color "$YELLOW" "Web interface will be available at: http://localhost:5000"
        python3 run_web.py
        ;;
        
    3)
        # AI single player
        if [ "$API_KEY_SET" = false ]; then
            print_color "$RED" "✗ AI mode requires OpenAI API key"
            exit 1
        fi
        
        print_color "$BLUE" "\n🤖 Launching AI mode (single player)..."
        
        # Check requirements
        if [ "$DOLPHIN_RUNNING" = false ]; then
            print_color "$YELLOW" "⚠ Warning: Dolphin is not running"
            echo -n "Continue anyway? (y/n): "
            read continue_anyway
            [ "$continue_anyway" != "y" ] && exit 0
        fi
        
        # Get player number
        echo -n "Which player should be AI? (0-3, default 0): "
        read ai_player
        ai_player=${ai_player:-0}
        
        print_color "$GREEN" "Starting AI for player $ai_player..."
        python3 src/ai/run_ai_mode.py --ai-players $ai_player
        ;;
        
    4)
        # AI multiple players
        if [ "$API_KEY_SET" = false ]; then
            print_color "$RED" "✗ AI mode requires OpenAI API key"
            exit 1
        fi
        
        print_color "$BLUE" "\n🤖 Launching AI mode (multiple players)..."
        
        # Get player numbers
        echo -n "Which players should be AI? (e.g., 0,2): "
        read ai_players
        ai_players=${ai_players:-"0,2"}
        
        # Get model
        echo -n "Which model to use? (gpt-4/gpt-3.5-turbo, default gpt-4): "
        read model
        model=${model:-"gpt-4"}
        
        print_color "$GREEN" "Starting AI for players $ai_players with model $model..."
        python3 src/ai/run_ai_mode.py --ai-players $ai_players --model $model
        ;;
        
    5)
        # Run tests
        print_color "$BLUE" "\n🧪 Running AI tests..."
        ./run_tests_final.sh
        ;;
        
    6)
        # Exit
        print_color "$GREEN" "Goodbye! 👋"
        exit 0
        ;;
        
    *)
        print_color "$RED" "Invalid choice"
        exit 1
        ;;
esac

# Keep script running if needed
if [ "$choice" != "5" ] && [ "$choice" != "6" ]; then
    print_color "$YELLOW" "\nPress Ctrl+C to stop"
    wait
fi