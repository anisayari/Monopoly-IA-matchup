import mss
import mss.tools
from PIL import Image
from typing import Optional
import datetime
import os
from pathlib import Path
import sys
import platform

# Platform-specific imports
if platform.system() == "Windows":
    import win32gui
    import pygetwindow as gw
elif platform.system() == "Darwin":  # macOS
    try:
        from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps
        import Quartz
    except ImportError:
        print("⚠️ For macOS, please install: pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz")
        sys.exit(1)

def get_dolphin_window_mac():
    """Find Dolphin window on macOS"""
    try:
        # Get all windows
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        
        dolphin_windows = []
        
        for window in window_list:
            window_title = window.get('kCGWindowName', '')
            app_name = window.get('kCGWindowOwnerName', '')
            
            if window_title and ('dolphin' in window_title.lower() or 'monopoly' in window_title.lower() or 
                                'dolphin' in app_name.lower()):
                bounds = window.get('kCGWindowBounds', {})
                if bounds.get('Width', 0) > 0 and bounds.get('Height', 0) > 0:
                    dolphin_windows.append({
                        'title': window_title or app_name,
                        'app': app_name,
                        'left': int(bounds.get('X', 0)),
                        'top': int(bounds.get('Y', 0)),
                        'width': int(bounds.get('Width', 0)),
                        'height': int(bounds.get('Height', 0))
                    })
        
        if not dolphin_windows:
            print("❌ No Dolphin window found!")
            return None
        
        if len(dolphin_windows) == 1:
            win = dolphin_windows[0]
            print(f"✅ Found Dolphin window: {win['title']} ({win['app']})")
            return win
        
        # Multiple windows - let user choose
        print("🔍 Multiple windows found:")
        for i, win in enumerate(dolphin_windows):
            print(f"   {i + 1}. {win['title']} ({win['app']})")
        
        while True:
            try:
                choice = int(input("Select window number: ")) - 1
                if 0 <= choice < len(dolphin_windows):
                    selected = dolphin_windows[choice]
                    print(f"✅ Selected: {selected['title']}")
                    return selected
                print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")
                
    except Exception as e:
        print(f"❌ Error finding windows on macOS: {e}")
        return None

def get_dolphin_window_windows():
    """Find Dolphin window on Windows"""
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

def get_dolphin_window():
    """Find Dolphin window based on platform"""
    current_platform = platform.system()
    
    if current_platform == "Windows":
        return get_dolphin_window_windows()
    elif current_platform == "Darwin":
        return get_dolphin_window_mac()
    else:
        print(f"❌ Unsupported platform: {current_platform}")
        return None

def main():
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print("🎮 Dolphin Screenshot Tool")
        print("Usage: python screenshot_script.py [--platform PLATFORM]")
        print("Options:")
        print("  --platform mac    Force macOS mode")
        print("  --platform win    Force Windows mode")
        print("  --help, -h        Show this help message")
        print("\nBy default, the script auto-detects your platform.")
        return
    
    # Check for platform override
    if len(sys.argv) > 2 and sys.argv[1] == "--platform":
        platform_override = sys.argv[2].lower()
        if platform_override == "mac":
            print("🍎 Forcing macOS mode...")
            platform.system = lambda: "Darwin"
        elif platform_override == "win":
            print("🪟 Forcing Windows mode...")
            platform.system = lambda: "Windows"
        else:
            print(f"❌ Unknown platform: {platform_override}")
            return
    
    print(f"🖥️  Running on: {platform.system()}")
    
    # Find and select window
    win = get_dolphin_window()
    if not win:
        return
    
    # Get window coordinates based on platform
    if platform.system() == "Windows":
        left, top = win.left, win.top
        width, height = win.width, win.height
    else:  # macOS or dict format
        if isinstance(win, dict):
            left, top = win['left'], win['top']
            width, height = win['width'], win['height']
        else:
            left, top = win.left, win.top
            width, height = win.width, win.height
    
    print("\n📷 Press ENTER to take a screenshot (Ctrl+C to exit)")
    print(f"📐 Window coordinates: left={left}, top={top}, width={width}, height={height}")
    
    try:
        while True:
            input()  # Wait for Enter key
            
            # Take screenshot using mss
            try:
                with mss.mss() as sct:
                    # Define monitor area from window
                    monitor = {
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height
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