#!/usr/bin/env python3
"""
Monopoly AI - Interactive Launcher
A user-friendly launcher for all Monopoly AI features.
"""

import os
import sys
import subprocess
import time
import requests
import signal
from typing import Optional, List, Tuple
import json

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header():
    """Print the application header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}🎮 Monopoly AI - Interactive Launcher 🎮{Colors.ENDC}")
    print("=" * 50)

def print_status(message: str, status: str = "info"):
    """Print a status message with color."""
    colors = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED
    }
    color = colors.get(status, Colors.BLUE)
    symbol = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}.get(status, "•")
    print(f"{color}{symbol} {message}{Colors.ENDC}")

def check_prerequisites() -> dict:
    """Check all prerequisites and return status."""
    status = {
        "python": False,
        "docker": False,
        "dolphin": False,
        "openai_key": False,
        "omniparser": False
    }
    
    print(f"\n{Colors.CYAN}Checking prerequisites...{Colors.ENDC}")
    
    # Check Python
    try:
        python_version = subprocess.check_output([sys.executable, "--version"], stderr=subprocess.STDOUT).decode().strip()
        status["python"] = True
        print_status(f"Python: {python_version}", "success")
    except:
        print_status("Python not found", "error")
    
    # Check Docker
    try:
        subprocess.check_output(["docker", "--version"], stderr=subprocess.DEVNULL)
        status["docker"] = True
        print_status("Docker is installed", "success")
    except:
        print_status("Docker not found (required for OmniParser)", "warning")
    
    # Check Dolphin process
    try:
        result = subprocess.run(["pgrep", "-f", "Dolphin"], capture_output=True)
        if result.returncode == 0:
            status["dolphin"] = True
            print_status("Dolphin is running", "success")
        else:
            print_status("Dolphin is not running", "warning")
    except:
        # Windows compatibility
        try:
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Dolphin.exe"], capture_output=True, text=True)
            if "Dolphin.exe" in result.stdout:
                status["dolphin"] = True
                print_status("Dolphin is running", "success")
            else:
                print_status("Dolphin is not running", "warning")
        except:
            print_status("Cannot check Dolphin status", "warning")
    
    # Check OpenAI key
    if os.environ.get("OPENAI_API_KEY"):
        status["openai_key"] = True
        print_status("OpenAI API key is set", "success")
    else:
        print_status("OpenAI API key not set", "warning")
    
    # Check OmniParser
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            status["omniparser"] = True
            print_status("OmniParser is running", "success")
    except:
        print_status("OmniParser is not running", "info")
    
    return status

def start_omniparser() -> bool:
    """Start OmniParser service."""
    print_status("Starting OmniParser...", "info")
    
    omniparser_dir = os.path.join(os.path.dirname(__file__), "omniparserserver")
    if not os.path.exists(omniparser_dir):
        print_status("OmniParser directory not found", "error")
        return False
    
    try:
        # Start docker-compose
        subprocess.Popen(
            ["docker-compose", "up", "-d"],
            cwd=omniparser_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for service to be ready
        print("Waiting for OmniParser to start", end="")
        for i in range(30):
            try:
                response = requests.get("http://localhost:8000/health", timeout=1)
                if response.status_code == 200:
                    print()
                    print_status("OmniParser started successfully", "success")
                    return True
            except:
                pass
            print(".", end="", flush=True)
            time.sleep(1)
        
        print()
        print_status("OmniParser failed to start", "error")
        return False
        
    except Exception as e:
        print_status(f"Error starting OmniParser: {e}", "error")
        return False

def get_ai_config() -> dict:
    """Get AI configuration from user."""
    config = {}
    
    print(f"\n{Colors.CYAN}AI Configuration:{Colors.ENDC}")
    
    # Get players
    players_input = input("Which players should be AI? (e.g., 0 or 0,2): ").strip()
    if not players_input:
        players_input = "0"
    config["players"] = players_input
    
    # Get model
    print("\nAvailable models:")
    print("1) gpt-4 (best performance)")
    print("2) gpt-3.5-turbo (faster, cheaper)")
    model_choice = input("Choose model (1-2, default 1): ").strip()
    
    if model_choice == "2":
        config["model"] = "gpt-3.5-turbo"
    else:
        config["model"] = "gpt-4"
    
    # Get temperature
    temp_input = input("Temperature (0.0-1.0, default 0.7): ").strip()
    try:
        config["temperature"] = float(temp_input) if temp_input else 0.7
    except:
        config["temperature"] = 0.7
    
    return config

def launch_mode(mode: str, status: dict):
    """Launch the selected mode."""
    if mode == "console":
        print_status("Launching console mode...", "info")
        subprocess.run([sys.executable, "main.py"])
        
    elif mode == "web":
        print_status("Launching web interface...", "info")
        print_status("Web interface will be available at: http://localhost:5000", "info")
        subprocess.run([sys.executable, "run_web.py"])
        
    elif mode == "ai":
        if not status["openai_key"]:
            print_status("AI mode requires OpenAI API key", "error")
            api_key = input("Enter your OpenAI API key: ").strip()
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            else:
                return
        
        # Start OmniParser if needed
        if status["docker"] and not status["omniparser"]:
            response = input("\nStart OmniParser for automatic clicks? (y/n): ").strip().lower()
            if response == "y":
                start_omniparser()
        
        # Get AI configuration
        config = get_ai_config()
        
        # Launch AI
        print_status(f"Launching AI for players {config['players']} with {config['model']}...", "info")
        cmd = [
            sys.executable, "src/ai/run_ai_mode.py",
            "--ai-players", config["players"],
            "--model", config["model"],
            "--temperature", str(config["temperature"])
        ]
        subprocess.run(cmd)
        
    elif mode == "test":
        print_status("Running AI tests...", "info")
        subprocess.run(["./run_tests_final.sh"])

def main_menu(status: dict):
    """Display main menu and get user choice."""
    print(f"\n{Colors.CYAN}Main Menu:{Colors.ENDC}")
    print("1) Console Mode - Monitor game events")
    print("2) Web Interface - Visual game control")
    
    if status["openai_key"] or True:  # Always show, will prompt for key
        print("3) AI Mode - Let AI play")
    
    print("4) Run Tests - Verify installation")
    print("5) Refresh Status")
    print("6) Exit")
    
    choice = input(f"\n{Colors.YELLOW}Your choice (1-6): {Colors.ENDC}").strip()
    
    return choice

def main():
    """Main launcher function."""
    print_header()
    
    # Initial status check
    status = check_prerequisites()
    
    while True:
        choice = main_menu(status)
        
        if choice == "1":
            launch_mode("console", status)
        elif choice == "2":
            launch_mode("web", status)
        elif choice == "3":
            launch_mode("ai", status)
        elif choice == "4":
            launch_mode("test", status)
        elif choice == "5":
            status = check_prerequisites()
        elif choice == "6":
            print_status("Goodbye! 👋", "success")
            break
        else:
            print_status("Invalid choice", "error")
        
        # Pause before showing menu again
        if choice in ["1", "2", "3", "4"]:
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print_status("\n\nStopping services...", "warning")
    
    # Stop OmniParser if running
    try:
        omniparser_dir = os.path.join(os.path.dirname(__file__), "omniparserserver")
        subprocess.run(
            ["docker-compose", "down"],
            cwd=omniparser_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
    except:
        pass
    
    print_status("Goodbye! 👋", "success")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        main()
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        sys.exit(1)