#!/usr/bin/env python3
"""
Complete calibration script that handles Dolphin launching and visual calibration
"""
import os
import sys
import time
import json
import subprocess
import win32gui
import win32process

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibration.visual_calibration import VisualDolphinCalibrator
import config


def load_config():
    """Load user configuration"""
    try:
        config_file = os.path.join("config", "user_config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
    
    # Default configuration
    return {
        "dolphin_path": config.DOLPHIN_PATH,
        "monopoly_iso_path": config.MONOPOLY_ISO_PATH,
        "save_file_path": config.SAVE_FILE_PATH
    }


def is_dolphin_running():
    """Check if Dolphin is already running"""
    def enum_windows_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # Look for actual Dolphin emulator window (not terminal windows)
            if ("dolphin" in window_text.lower() and 
                ("monopoly" in window_text.lower() or 
                 "jit" in window_text.lower() or 
                 "direct3d" in window_text.lower() or
                 "opengl" in window_text.lower() or
                 class_name == "Qt5QWindowIcon")):
                windows.append((hwnd, window_text))
    
    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    return len(windows) > 0


def start_dolphin(config_data):
    """Start Dolphin with the game"""
    dolphin_path = config_data.get("dolphin_path")
    iso_path = config_data.get("monopoly_iso_path")
    save_path = config_data.get("save_file_path")
    
    if not dolphin_path or not os.path.exists(dolphin_path):
        print(f"Dolphin not found: {dolphin_path}")
        return None
    
    if not iso_path or not os.path.exists(iso_path):
        print(f"Monopoly ISO not found: {iso_path}")
        return None
    
    print("Starting Dolphin...")
    print(f"   Dolphin: {dolphin_path}")
    print(f"   ISO: {iso_path}")
    
    try:
        # Command to launch Dolphin
        cmd = [dolphin_path, '-b', '-e', iso_path]
        
        # Add save file if it exists
        if save_path and os.path.exists(save_path):
            cmd.extend(['-s', save_path])
            print(f"   Save file: {save_path}")
        
        # Start Dolphin
        process = subprocess.Popen(cmd)
        
        print(f"Dolphin started (PID: {process.pid})")
        print("Waiting for Dolphin to be ready...")
        
        # Wait for Dolphin window to appear
        start_time = time.time()
        dolphin_found = False
        
        while time.time() - start_time < 45:  # 45 second timeout
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if "dolphin" in window_text.lower():
                        windows.append((hwnd, window_text))
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if windows:
                print(f"Dolphin window detected: {windows[0][1]}")
                dolphin_found = True
                
                # Wait for game to load (Monopoly in title)
                if "monopoly" in windows[0][1].lower():
                    print("Monopoly game loaded")
                    time.sleep(3)  # Wait a bit more for everything to be ready
                    return process
                else:
                    print("Waiting for game to load...")
            
            time.sleep(2)
        
        if dolphin_found:
            print("Dolphin is open but the game might not be fully loaded")
            print("   You can continue with calibration manually")
        else:
            print("Timeout: Could not detect Dolphin window")
            print("   Check that Dolphin opened correctly")
        
        return process
        
    except Exception as e:
        print(f"Error starting Dolphin: {e}")
        return None


def main():
    """Main function"""
    print("🎮 Monopoly Visual Calibration Tool")
    print("=" * 55)
    print()
    
    # Load configuration
    config_data = load_config()
    
    # Check if Dolphin is already running
    dolphin_already_running = is_dolphin_running()
    dolphin_process = None
    
    if dolphin_already_running:
        print("✅ Dolphin is already running")
        print()
    else:
        print("❌ Dolphin is not running")
        
        # Check paths
        if not config_data.get("dolphin_path"):
            print("Dolphin path not configured")
            print("   Please run the web interface first to configure paths")
            input("\nPress Enter to exit...")
            return False
        
        # Ask if user wants to start Dolphin
        response = input("\nDo you want to start Dolphin? (Y/N): ")
        if response.upper() == 'Y':
            dolphin_process = start_dolphin(config_data)
            if not dolphin_process:
                print("Could not start Dolphin")
                input("\nPress Enter to exit...")
                return False
        else:
            print("\nPlease start Dolphin manually before running calibration")
            input("\nPress Enter to exit...")
            return False
    
    # Now run the visual calibration
    print("\n" + "="*55)
    print("Starting Visual Calibration...")
    print("="*55)
    
    try:
        calibrator = VisualDolphinCalibrator()
        
        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            print("\n✅ Calibration completed successfully!")
            print("💡 The blue overlay helped you align accurately")
            calibration_success = True
        else:
            print("\n❌ Calibration failed or was cancelled")
            calibration_success = False
            
    except Exception as e:
        print(f"\n💥 Error during calibration: {e}")
        import traceback
        traceback.print_exc()
        calibration_success = False
    
    # If we started Dolphin, ask if user wants to keep it open
    if dolphin_process and not dolphin_already_running:
        print("\n" + "="*55)
        response = input("\nDo you want to keep Dolphin open? (Y/N): ")
        if response.upper() != 'Y':
            print("Stopping Dolphin...")
            try:
                dolphin_process.terminate()
                dolphin_process.wait(timeout=5)
                print("Dolphin stopped")
            except:
                dolphin_process.kill()
                print("Dolphin force closed")
    
    print("\n" + "="*55)
    if calibration_success:
        print("Calibration completed! You can now use the system.")
    else:
        print("Calibration not completed. Please try again.")
    
    input("\nPress Enter to exit...")
    return calibration_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)