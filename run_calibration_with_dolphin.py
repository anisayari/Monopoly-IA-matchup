#!/usr/bin/env python3
"""
Script de calibration qui lance et ferme Dolphin automatiquement
"""
import os
import sys
import time
import json
import subprocess
import win32gui
import win32process
from calibration.visual_calibration import VisualDolphinCalibrator as DolphinCalibrator
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
        # Commande pour lancer Dolphin
        cmd = [dolphin_path, '-b', '-e', iso_path]
        
        # Add save file if it exists
        if save_path and os.path.exists(save_path):
            cmd.extend(['-s', save_path])
            print(f"   Save file: {save_path}")
        
        # Start Dolphin
        process = subprocess.Popen(cmd)
        
        print(f"Dolphin started (PID: {process.pid})")
        print("Waiting for Dolphin to be ready...")
        
        # Attendre que la fenêtre Dolphin apparaisse
        start_time = time.time()
        dolphin_found = False
        
        while time.time() - start_time < 45:  # Timeout de 45 secondes
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

def stop_dolphin(process):
    """Stop Dolphin cleanly"""
    if not process:
        return
    
    print("Stopping Dolphin...")
    
    try:
        # Essayer d'abord de fermer proprement
        process.terminate()
        
        # Attendre jusqu'à 5 secondes
        try:
            process.wait(timeout=5)
            print("Dolphin stopped cleanly")
        except subprocess.TimeoutExpired:
            # Force close if necessary
            process.kill()
            print("Dolphin forced to close")
            
    except Exception as e:
        print(f"Error stopping Dolphin: {e}")
    
    # Clean up remaining Dolphin processes
    print("Cleaning up remaining processes...")
    
    try:
        # Arrêter Dolphin
        result = subprocess.run(['taskkill', '/F', '/IM', 'Dolphin.exe'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("Dolphin.exe processes cleaned")
    except Exception as e:
        print(f"Error cleaning Dolphin: {e}")
    
    try:
        # Stop DolphinMemoryEngine
        result = subprocess.run(['taskkill', '/F', '/IM', 'DolphinMemoryEngine.exe'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("DolphinMemoryEngine.exe processes cleaned")
    except Exception as e:
        print(f"Error cleaning DolphinMemoryEngine: {e}")
    
    # Petite pause pour que le nettoyage soit effectif
    time.sleep(1)

def main():
    """Main function"""
    print("Monopoly Calibration with Automatic Dolphin")
    print("=" * 55)
    print()
    
    # Load configuration
    config_data = load_config()
    
    # Check paths
    if not config_data.get("dolphin_path"):
        print("Dolphin path not configured")
        print("   Please run the web interface first to configure paths")
        input("\nPress Enter to exit...")
        return False
    
    dolphin_process = None
    calibration_success = False
    
    try:
        # 1. Start Dolphin
        dolphin_process = start_dolphin(config_data)
        if not dolphin_process:
            print("Could not start Dolphin")
            return False
        
        print("\nInstructions:")
        print("   1. Dolphin will open with Monopoly")
        print("   2. Wait for the game to load")
        print("   3. Follow the calibration instructions")
        print("   4. Dolphin will close automatically when done")
        print()
        
        input("Press Enter when Dolphin is ready to start calibration...")
        
        # 2. Start calibration
        print("\nStarting calibration...")
        calibrator = DolphinCalibrator()
        
        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            
            # Créer les fonctions de transformation
            m2w, w2m = calibrator.create_transformation_functions()
            
            if m2w and w2m:
                print("\nCalibration completed successfully!")
                calibration_success = True
                
                # Test transformation
                test_point = calibrator.calibration_points[0]
                converted_x, converted_y = m2w(test_point.mouse_x, test_point.mouse_y)
                print(f"\nConversion test:")
                print(f"   Original: Mouse({test_point.mouse_x}, {test_point.mouse_y}) -> Wiimote({test_point.wiimote_x}, {test_point.wiimote_y})")
                print(f"   Calculated: Mouse({test_point.mouse_x}, {test_point.mouse_y}) -> Wiimote({converted_x:.1f}, {converted_y:.1f})")
            else:
                print("\nCalibration completed but transformation functions could not be created")
        else:
            print("\nCalibration failed or cancelled")
    
    except KeyboardInterrupt:
        print("\n\nCalibration interrupted by user")
    except Exception as e:
        print(f"\nError during calibration: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 3. Stop Dolphin in all cases
        if dolphin_process:
            print("\n" + "="*55)
            stop_dolphin(dolphin_process)
    
    print("\n" + "="*55)
    if calibration_success:
        print("Calibration completed! You can now launch the web interface.")
    else:
        print("Calibration not completed. You can retry from the web interface.")
    
    input("\nPress Enter to continue...")
    return calibration_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)