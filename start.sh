#!/bin/bash
# Quick start script - launches the interactive launcher

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: Please run this script from the Monopoly-IA-matchup directory"
    exit 1
fi

# Use Python launcher for better experience
if command -v python3 &> /dev/null; then
    python3 launcher.py
else
    echo "Error: Python 3 is required"
    echo "Please install Python 3 first"
    exit 1
fi