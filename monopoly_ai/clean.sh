#!/bin/bash
# Clean up generated files and caches

echo "Cleaning Monopoly AI project..."

# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove generated game history files
rm -f game_history_*.json

# Remove .pyc files
find . -name "*.pyc" -delete 2>/dev/null || true

# Remove .pyo files
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove .DS_Store files (macOS)
find . -name ".DS_Store" -delete 2>/dev/null || true

echo "✓ Cleanup complete!"