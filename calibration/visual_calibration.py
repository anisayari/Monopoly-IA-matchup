import os
import sys
import win32gui
import win32api
import win32con
import time
import json
import tkinter as tk
from dataclasses import dataclass
from typing import List, Tuple, Optional
import threading

@dataclass
class CalibrationPoint:
    """Represents a calibration point with mouse and Wiimote coordinates"""
    mouse_x: int
    mouse_y: int
    wiimote_x: float
    wiimote_y: float
    point_number: int


class VisualDolphinCalibrator:
    def __init__(self):
        self.dolphin_hwnd: Optional[int] = None
        self.calibration_points: List[CalibrationPoint] = []
        self.current_point = 0
        self.corner_names = ["upper left", "upper right", "lower right", "lower left"]
        self.overlay_window = None
        self.canvas = None
        self.root = None
        self.running = True
        self.click_detected = False
        self.last_click_pos = (0, 0)

    def find_dolphin_window(self) -> bool:
        """Find the Dolphin emulator window"""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                # Filter for actual Dolphin emulator windows only
                if (("dolphin" in window_text.lower() and 
                     ("monopoly" in window_text.lower() or 
                      "jit" in window_text.lower() or 
                      "direct3d" in window_text.lower() or
                      "opengl" in window_text.lower())) or
                    class_name == "Qt5QWindowIcon"):
                    windows.append((hwnd, window_text))

        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)

        if not windows:
            print("❌ No Dolphin window found!")
            print("   Make sure Dolphin is running and visible")
            return False

        if len(windows) == 1:
            self.dolphin_hwnd, window_title = windows[0]
            print(f"✅ Found Dolphin window: {window_title}")
            return True

        # Multiple windows found, let user choose
        print("🔍 Multiple windows found:")
        for i, (hwnd, title) in enumerate(windows):
            print(f"   {i + 1}. {title}")

        while True:
            try:
                choice = int(input("Select window number: ")) - 1
                if 0 <= choice < len(windows):
                    self.dolphin_hwnd, window_title = windows[choice]
                    print(f"✅ Selected: {window_title}")
                    return True
                else:
                    print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")

    def create_overlay(self):
        """Create a semi-transparent overlay window"""
        if not self.dolphin_hwnd:
            return

        # Get Dolphin window position and size
        window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
        
        # Calculate window decorations
        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x
        
        # Create Tkinter window
        self.root = tk.Tk()
        self.root.title("Calibration Helper")
        
        # Position the window over Dolphin
        x = window_rect[0] + border_x
        y = window_rect[1] + title_height
        width = client_rect[2]
        height = client_rect[3]
        
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make window transparent and always on top
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Create canvas with blue background
        self.canvas = tk.Canvas(self.root, width=width, height=height, 
                               bg='blue', highlightthickness=0)
        self.canvas.pack()
        
        # Draw corner markers
        marker_size = 20
        marker_color = 'yellow'
        marker_width = 3
        
        # Draw crosshairs at each corner
        corners = [
            (0, 0),  # upper left
            (width, 0),  # upper right
            (width, height),  # lower right
            (0, height)  # lower left
        ]
        
        for i, (cx, cy) in enumerate(corners):
            # Horizontal line
            self.canvas.create_line(cx - marker_size, cy, cx + marker_size, cy,
                                   fill=marker_color, width=marker_width, tags=f"corner{i}")
            # Vertical line
            self.canvas.create_line(cx, cy - marker_size, cx, cy + marker_size,
                                   fill=marker_color, width=marker_width, tags=f"corner{i}")
            # Corner label
            offset = 30
            if i == 0:  # upper left
                self.canvas.create_text(cx + offset, cy + offset, text=self.corner_names[i],
                                       fill='white', font=('Arial', 12, 'bold'), anchor='nw')
            elif i == 1:  # upper right
                self.canvas.create_text(cx - offset, cy + offset, text=self.corner_names[i],
                                       fill='white', font=('Arial', 12, 'bold'), anchor='ne')
            elif i == 2:  # lower right
                self.canvas.create_text(cx - offset, cy - offset, text=self.corner_names[i],
                                       fill='white', font=('Arial', 12, 'bold'), anchor='se')
            else:  # lower left
                self.canvas.create_text(cx + offset, cy - offset, text=self.corner_names[i],
                                       fill='white', font=('Arial', 12, 'bold'), anchor='sw')
        
        # Current point indicator
        self.status_text = self.canvas.create_text(width // 2, height // 2 - 50,
                                                  text="", fill='white', 
                                                  font=('Arial', 16, 'bold'))
        self.instruction_text = self.canvas.create_text(width // 2, height // 2,
                                                       text="", fill='yellow',
                                                       font=('Arial', 14))
        
        # Make overlay click-through
        self.root.bind('<Button-1>', lambda e: self.root.lower())
        
    def update_overlay(self):
        """Update overlay with current calibration point"""
        if not self.canvas:
            return
            
        corner_name = self.corner_names[self.current_point]
        self.canvas.itemconfig(self.status_text, 
                              text=f"Calibrating Point {self.current_point + 1}/4: {corner_name}")
        self.canvas.itemconfig(self.instruction_text,
                              text="Point Wiimote at the corner and right-click")
        
        # Highlight current corner
        for i in range(4):
            color = 'red' if i == self.current_point else 'yellow'
            width = 5 if i == self.current_point else 3
            for item in self.canvas.find_withtag(f"corner{i}"):
                self.canvas.itemconfig(item, fill=color, width=width)

    def close_overlay(self):
        """Close the overlay window"""
        if self.root:
            self.root.quit()
            self.root.destroy()

    def get_window_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to window-relative coordinates"""
        if not self.dolphin_hwnd:
            return x, y

        try:
            if not win32gui.IsWindow(self.dolphin_hwnd):
                raise Exception("Dolphin window no longer exists")
                
            window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
            client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

            border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
            title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

            rel_x = x - window_rect[0] - border_x
            rel_y = y - window_rect[1] - title_height

            return rel_x, rel_y
        except Exception as e:
            print(f"⚠️  Error getting window coordinates: {e}")
            return x, y

    def get_corner_coordinates(self, corner_index: int) -> Tuple[int, int]:
        """Get the coordinates of window corners"""
        if not self.dolphin_hwnd:
            return 0, 0

        try:
            if not win32gui.IsWindow(self.dolphin_hwnd):
                raise Exception("Dolphin window no longer exists")
                
            client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]

            corners = [
                (0, 0),  # upper left
                (width, 0),  # upper right
                (width, height),  # lower right
                (0, height)  # lower left
            ]

            return corners[corner_index]
        except Exception as e:
            print(f"❌ Error getting window coordinates: {e}")
            raise

    def is_point_in_dolphin_window(self, x: int, y: int) -> bool:
        """Check if a point is inside the Dolphin window"""
        if not self.dolphin_hwnd:
            return False

        hwnd = win32gui.WindowFromPoint((x, y))
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def monitor_clicks(self):
        """Monitor for right clicks in a separate thread"""
        prev_right_button = False
        
        while self.running:
            try:
                right_button_down = win32api.GetKeyState(win32con.VK_RBUTTON) < 0
                
                if right_button_down and not prev_right_button:
                    cursor_pos = win32gui.GetCursorPos()
                    
                    if self.is_point_in_dolphin_window(*cursor_pos):
                        self.last_click_pos = self.get_window_coordinates(*cursor_pos)
                        self.click_detected = True
                
                prev_right_button = right_button_down
                time.sleep(0.01)
                
            except Exception:
                time.sleep(0.1)

    def wait_for_click(self, corner_name: str, corner_x: int, corner_y: int) -> Tuple[int, int]:
        """Wait for a right-click and return the coordinates"""
        print(f"\n🎯 Point {self.current_point + 1}/4: {corner_name}")
        print(f"   Target corner: ({corner_x}, {corner_y})")
        print(f"   1. Align your Wiimote to point at the {corner_name} corner (yellow crosshair)")
        print("   2. Right-click anywhere in the Dolphin window")
        
        # Update overlay
        self.update_overlay()
        
        # Reset click detection
        self.click_detected = False
        
        # Wait for click
        while not self.click_detected and self.running:
            time.sleep(0.01)
            if self.root:
                self.root.update()
        
        # Wait for button release
        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            time.sleep(0.01)
        
        return self.last_click_pos

    def calibrate(self) -> bool:
        """Main calibration process"""
        print("🎮 Dolphin Visual Calibration Tool")
        print("=" * 40)

        if not self.find_dolphin_window():
            return False

        print("\n📋 Instructions:")
        print("   1. A blue overlay will appear over Dolphin")
        print("   2. Yellow crosshairs mark the corners")
        print("   3. Point your Wiimote at each corner")
        print("   4. Right-click to record the position")
        print("   5. Press Ctrl+C anytime to cancel")

        input("\nPress Enter when ready to start calibration...")

        if not win32gui.IsWindow(self.dolphin_hwnd):
            print("\n❌ Dolphin window was closed!")
            return False

        # Create overlay window
        self.create_overlay()
        
        # Start click monitoring thread
        click_thread = threading.Thread(target=self.monitor_clicks, daemon=True)
        click_thread.start()

        try:
            for i in range(4):
                self.current_point = i
                corner_name = self.corner_names[i]

                corner_x, corner_y = self.get_corner_coordinates(i)
                click_x, click_y = self.wait_for_click(corner_name, corner_x, corner_y)
                
                print(f"✅ Clicked at: ({click_x}, {click_y}) when pointing at {corner_name}")

                point = CalibrationPoint(
                    mouse_x=click_x,
                    mouse_y=click_y,
                    wiimote_x=float(corner_x),
                    wiimote_y=float(corner_y),
                    point_number=i + 1
                )
                self.calibration_points.append(point)
                print(f"✅ Point {i + 1} saved: Click({click_x}, {click_y}) → Corner({corner_x}, {corner_y})")

        except KeyboardInterrupt:
            print("\n❌ Calibration cancelled by user")
            return False
        finally:
            self.running = False
            self.close_overlay()

        return True

    def save_calibration(self, filename: str = None) -> None:
        """Save calibration data to JSON file"""
        if filename is None:
            # Get the absolute path to the project root
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            filename = os.path.join(project_root, "game_files", "calibration.json")
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        window_title = "Dolphin"
        window_width = 2048
        window_height = 1080
        
        if self.dolphin_hwnd:
            try:
                if win32gui.IsWindow(self.dolphin_hwnd):
                    window_title = win32gui.GetWindowText(self.dolphin_hwnd) or "Dolphin"
                    client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
                    window_width = client_rect[2] or 2048
                    window_height = client_rect[3] or 1080
            except Exception as e:
                print(f"Warning: Could not get window info: {e}")
                # Use defaults based on calibration points
                if len(self.calibration_points) >= 3:
                    window_width = int(max(p.wiimote_x for p in self.calibration_points))
                    window_height = int(max(p.wiimote_y for p in self.calibration_points))

        calibration_data = {
            "window_title": window_title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "window_size": {
                "width": window_width,
                "height": window_height
            },
            "points": [
                {
                    "point_number": point.point_number,
                    "mouse": {"x": point.mouse_x, "y": point.mouse_y},
                    "wiimote": {"x": point.wiimote_x, "y": point.wiimote_y}
                }
                for point in self.calibration_points
            ]
        }

        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)

        print(f"💾 Calibration saved to {filename}")

    def display_results(self):
        """Display calibration results"""
        print("\n🎯 Calibration Results:")
        print("=" * 50)

        for i, point in enumerate(self.calibration_points):
            corner_name = self.corner_names[i]
            print(f"Point {point.point_number} ({corner_name}):")
            print(f"   Click:  ({point.mouse_x:>4}, {point.mouse_y:>4})")
            print(f"   Target: ({point.wiimote_x:>6.1f}, {point.wiimote_y:>6.1f})")

            offset_x = abs(point.mouse_x - point.wiimote_x)
            offset_y = abs(point.mouse_y - point.wiimote_y)
            offset_distance = (offset_x ** 2 + offset_y ** 2) ** 0.5
            print(f"   Offset: {offset_distance:.1f} pixels")
            print()


def main():
    """Main function to run the visual calibration tool"""
    try:
        calibrator = VisualDolphinCalibrator()

        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            print("\n✅ Calibration completed successfully!")
            print("💡 The blue overlay helped you align accurately")
        else:
            print("\n❌ Calibration failed or was cancelled")

    except Exception as e:
        print(f"\n💥 Error during calibration: {e}")
        import traceback
        traceback.print_exc()

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()