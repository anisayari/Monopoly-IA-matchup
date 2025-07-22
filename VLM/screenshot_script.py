import win32gui
import pygetwindow as gw
import mss
import mss.tools
from PIL import Image
from typing import Optional
import datetime
import os
from pathlib import Path

def get_dolphin_window():
    """Find Dolphin window using pygetwindow (same as monitor_centralized)"""
    try:
        # Try with exact title first
        windows = gw.getWindowsWithTitle("SMPP69")
        for w in windows:
            if "monopoly" in w.title.lower() and w.width > 0 and w.height > 0:
                print(f"🖼️ Window found: {w.title}")
                return w
    except:
        pass
    
    # Fallback to searching all windows
    try:
        all_windows = gw.getAllWindows()
        dolphin_windows = []
        
        for w in all_windows:
            if w.title and ("dolphin" in w.title.lower() or "monopoly" in w.title.lower()) and w.width > 0 and w.height > 0:
                dolphin_windows.append(w)
        
        if not dolphin_windows:
            print("❌ No Dolphin window found!")
            return None
        
        if len(dolphin_windows) == 1:
            print(f"✅ Found Dolphin window: {dolphin_windows[0].title}")
            return dolphin_windows[0]
        
        # Multiple windows - let user choose
        print("🔍 Multiple windows found:")
        for i, w in enumerate(dolphin_windows):
            print(f"   {i + 1}. {w.title}")
        
        while True:
            try:
                choice = int(input("Select window number: ")) - 1
                if 0 <= choice < len(dolphin_windows):
                    selected = dolphin_windows[choice]
                    print(f"✅ Selected: {selected.title}")
                    return selected
                print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")
    except Exception as e:
        print(f"❌ Error finding windows: {e}")
        return None

def main():
    # Find and select window
    win = get_dolphin_window()
    if not win:
        return
    
    print("\n📷 Press ENTER to take a screenshot (Ctrl+C to exit)")
    print(f"📐 Window coordinates: left={win.left}, top={win.top}, width={win.width}, height={win.height}")
    
    try:
        while True:
            input()  # Wait for Enter key
            
            # Take screenshot using mss (same as monitor_centralized)
            try:
                with mss.mss() as sct:
                    # Define monitor area from window
                    monitor = {
                        "left": win.left,
                        "top": win.top,
                        "width": win.width,
                        "height": win.height
                    }
                    
                    # Capture screenshot
                    img = sct.grab(monitor)
                    
                    # Convert to PIL Image
                    img_pil = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')
                    
                    # Create screenshots directory if it doesn't exist
                    screenshots_dir = Path("screenshots")
                    screenshots_dir.mkdir(exist_ok=True)
                    
                    # Save screenshot in the screenshots directory
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"dolphin_screenshot_{timestamp}.png"
                    filepath = screenshots_dir / filename
                    img_pil.save(filepath)
                    
                    print(f"✅ Screenshot saved as: {filepath}")
                    print(f"📸 Image size: {img_pil.size[0]}x{img_pil.size[1]} pixels")
                
            except Exception as e:
                print(f"❌ Error taking screenshot: {e}")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()