#!/usr/bin/env python3
"""
Vérifie si la calibration existe et est valide
"""
import os
import json
import sys
from datetime import datetime, timedelta

CALIBRATION_FILE = os.path.join("game_files", "calibration.json")
MAX_AGE_DAYS = 30  # Recalibrer si plus de 30 jours

def check_calibration_status():
    """Check calibration status"""
    
    # Check if file exists
    if not os.path.exists(CALIBRATION_FILE):
        print("No calibration found")
        return False
    
    try:
        # Lire le fichier de calibration
        with open(CALIBRATION_FILE, 'r') as f:
            calibration_data = json.load(f)
        
        # Check if data is complete
        if "points" not in calibration_data or len(calibration_data["points"]) < 4:
            print("Incomplete calibration")
            return False
        
        # Check calibration age
        if "timestamp" in calibration_data:
            timestamp_str = calibration_data["timestamp"]
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            age = datetime.now() - timestamp
            
            if age > timedelta(days=MAX_AGE_DAYS):
                print(f"Calibration too old ({age.days} days)")
                return False
            else:
                print(f"Valid calibration (created {age.days} days ago)")
                return True
        else:
            print("No timestamp in calibration")
            return False
            
    except Exception as e:
        print(f"Error reading calibration: {e}")
        return False

def main():
    """Main entry point"""
    is_valid = check_calibration_status()
    
    # Return 0 if valid, 1 otherwise
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()