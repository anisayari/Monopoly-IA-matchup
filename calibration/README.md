# Dolphin Wiimote Calibration Tools

Tools for calibrating mouse-to-Wiimote coordinate mapping in Dolphin emulator.

## Files

**`run_calibration.py`** - Create calibration by clicking 4 point pairs  
**`test_calibration.py`** - Visual test showing real-time Wiimote cursor position  
**`calibration.py`** - Core coordinate transformation utilities

## Usage

1. **Calibrate**: `python run_calibration.py`
   - Right-click 4 points in Dolphin window
   - Right-click corresponding Wiimote positions
   - Choose different screen areas (corners work best)

2. **Test**: `python test_calibration.py`
   - Move mouse over Dolphin to see Wiimote cursor
   - Red dot shows where Wiimote would point

Calibration saves to `../game_files/calibration.json`