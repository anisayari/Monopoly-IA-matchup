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
        # 9 point grid: 3x3 layout for better precision
        self.point_names = [
            "top-left", "top-center", "top-right",
            "middle-left", "center", "middle-right",
            "bottom-left", "bottom-center", "bottom-right"
        ]
        self.overlay_window = None
        self.canvas = None
        self.root = None
        self.running = True
        self.click_detected = False
        self.last_click_pos = (0, 0)
        self.grid_positions = []
        # Overlay tracking attributes
        self.overlay_x = 0
        self.overlay_y = 0
        self.overlay_width = 0
        self.overlay_height = 0

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

    def get_grid_positions(self, width: int, height: int) -> List[Tuple[int, int]]:
        """Calculate 9 grid positions (3x3) with margins for better precision"""
        margin_x = width * 0.1  # 10% margin
        margin_y = height * 0.1  # 10% margin

        # Usable area
        usable_width = width - 2 * margin_x
        usable_height = height - 2 * margin_y

        positions = []
        for row in range(3):
            for col in range(3):
                x = margin_x + col * usable_width / 2
                y = margin_y + row * usable_height / 2
                positions.append((int(x), int(y)))

        return positions

    def create_overlay(self):
        """Create a simple working overlay window with 9-point grid"""
        if not self.dolphin_hwnd:
            return

        # Get Dolphin window position and size
        window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

        # Calculate window decorations
        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

        # Store position for tracking
        self.overlay_x = window_rect[0] + border_x
        self.overlay_y = window_rect[1] + title_height
        self.overlay_width = client_rect[2]
        self.overlay_height = client_rect[3]

        # Create simple Tkinter window
        self.root = tk.Tk()
        self.root.title("Calibration Overlay")
        self.root.geometry(f"{self.overlay_width}x{self.overlay_height}+{self.overlay_x}+{self.overlay_y}")

        # Simple transparent settings - clicks go through transparent areas
        self.root.attributes('-alpha', 0.8)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.wm_attributes('-transparentcolor', 'black')  # Make black transparent

        # Create canvas with transparent background
        self.canvas = tk.Canvas(self.root, width=self.overlay_width, height=self.overlay_height,
                                bg='black', highlightthickness=0)  # Black = transparent
        self.canvas.pack()

        # Get grid positions
        self.grid_positions = self.get_grid_positions(self.overlay_width, self.overlay_height)

        # Draw minimal calibration points
        self.draw_calibration_points()

        # Simple window tracking every 200ms
        self.track_window()

    def draw_calibration_points(self):
        """Draw minimal 9 calibration points - small crosses only"""
        marker_size = 12  # Much smaller

        for i, (cx, cy) in enumerate(self.grid_positions):
            # Small yellow crosshair
            self.canvas.create_line(cx - marker_size, cy, cx + marker_size, cy,
                                    fill='yellow', width=2, tags=f"point{i}")
            self.canvas.create_line(cx, cy - marker_size, cx, cy + marker_size,
                                    fill='yellow', width=2, tags=f"point{i}")

            # Small white center dot
            self.canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2,
                                    fill='white', outline='black', width=1, tags=f"point{i}")

    def track_window(self):
        """Simple window position tracking"""
        if not self.running or not self.root:
            return

        try:
            if win32gui.IsWindow(self.dolphin_hwnd):
                window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
                client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

                border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
                title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

                new_x = window_rect[0] + border_x
                new_y = window_rect[1] + title_height

                # Only update if position changed significantly
                if abs(new_x - self.overlay_x) > 5 or abs(new_y - self.overlay_y) > 5:
                    self.overlay_x = new_x
                    self.overlay_y = new_y
                    self.root.geometry(f"{self.overlay_width}x{self.overlay_height}+{new_x}+{new_y}")

            # Schedule next check
            self.root.after(200, self.track_window)
        except:
            pass

    def update_overlay(self):
        """Update overlay with current calibration point - minimal visual feedback"""
        if not self.canvas:
            return

        # Highlight current point with enhanced visibility
        for i in range(9):
            if i == self.current_point:
                # Current point: bright red
                color = 'red'
                width = 3
            else:
                # Other points: normal yellow
                color = 'yellow'
                width = 2

            # Update crosshair color
            for item in self.canvas.find_withtag(f"point{i}"):
                if self.canvas.type(item) == 'line':
                    self.canvas.itemconfig(item, fill=color, width=width)

    def close_overlay(self):
        """Close the overlay window"""
        self.running = False  # Stop tracking first
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
                self.root = None
            except:
                pass

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

    def get_point_coordinates(self, point_index: int) -> Tuple[int, int]:
        """Get the coordinates of grid points"""
        if not self.dolphin_hwnd:
            return 0, 0

        try:
            if not win32gui.IsWindow(self.dolphin_hwnd):
                raise Exception("Dolphin window no longer exists")

            client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]

            grid_positions = self.get_grid_positions(width, height)
            return grid_positions[point_index]
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

    def wait_for_click(self, point_name: str, point_x: int, point_y: int) -> Tuple[int, int]:
        """Wait for a right-click and return the coordinates"""
        print(f"\n🎯 Point {self.current_point + 1}/9: {point_name}")
        print(f"   Target position: ({point_x}, {point_y})")
        print(f"   1. Align your Wiimote to point at the WHITE DOT at {point_name}")
        print("   2. Right-click anywhere in the Dolphin window when aligned")

        # Update overlay
        self.update_overlay()

        # Reset click detection
        self.click_detected = False

        # Wait for click with simple updates
        while not self.click_detected and self.running:
            time.sleep(0.01)
            if self.root:
                try:
                    self.root.update()  # Simple update
                except:
                    break

        # Wait for button release
        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            time.sleep(0.01)

        return self.last_click_pos

    def calibrate(self) -> bool:
        """Main calibration process with 9-point grid"""
        print("🎮 Enhanced Dolphin Visual Calibration Tool")
        print("=" * 50)

        if not self.find_dolphin_window():
            return False

        print("\n📋 Enhanced Instructions:")
        print("   1. A blue overlay will appear with a 3×3 grid of crosshairs")
        print("   2. Each point has a WHITE DOT for precise aiming")
        print("   3. Point your Wiimote at each WHITE DOT precisely")
        print("   4. Right-click to record each position (9 points total)")
        print("   5. More points = better accuracy across the screen")
        print("   6. Press Ctrl+C anytime to cancel")

        input("\nPress Enter when ready to start enhanced calibration...")

        if not win32gui.IsWindow(self.dolphin_hwnd):
            print("\n❌ Dolphin window was closed!")
            return False

        # Create overlay window
        self.create_overlay()

        # Start click monitoring thread
        click_thread = threading.Thread(target=self.monitor_clicks, daemon=True)
        click_thread.start()

        try:
            for i in range(9):  # 9 points instead of 4
                self.current_point = i
                point_name = self.point_names[i]

                point_x, point_y = self.get_point_coordinates(i)
                click_x, click_y = self.wait_for_click(point_name, point_x, point_y)

                print(f"✅ Clicked at: ({click_x}, {click_y}) when pointing at {point_name}")

                point = CalibrationPoint(
                    mouse_x=click_x,
                    mouse_y=click_y,
                    wiimote_x=float(point_x),
                    wiimote_y=float(point_y),
                    point_number=i + 1
                )
                self.calibration_points.append(point)
                print(f"✅ Point {i + 1} saved: Click({click_x}, {click_y}) → Target({point_x}, {point_y})")

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
            "calibration_type": "9-point-grid",  # Mark as enhanced calibration
            "window_size": {
                "width": window_width,
                "height": window_height
            },
            "points": [
                {
                    "point_number": point.point_number,
                    "point_name": self.point_names[i],
                    "mouse": {"x": point.mouse_x, "y": point.mouse_y},
                    "wiimote": {"x": point.wiimote_x, "y": point.wiimote_y}
                }
                for i, point in enumerate(self.calibration_points)
            ]
        }

        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)

        print(f"💾 Enhanced calibration saved to {filename}")

    def display_results(self):
        """Display calibration results"""
        print("\n🎯 Enhanced Calibration Results (9-Point Grid):")
        print("=" * 60)

        total_offset = 0
        for i, point in enumerate(self.calibration_points):
            point_name = self.point_names[i]
            print(f"Point {point.point_number} ({point_name}):")
            print(f"   Click:  ({point.mouse_x:>4}, {point.mouse_y:>4})")
            print(f"   Target: ({point.wiimote_x:>6.1f}, {point.wiimote_y:>6.1f})")

            offset_x = abs(point.mouse_x - point.wiimote_x)
            offset_y = abs(point.mouse_y - point.wiimote_y)
            offset_distance = (offset_x ** 2 + offset_y ** 2) ** 0.5
            total_offset += offset_distance
            print(f"   Offset: {offset_distance:.1f} pixels")
            print()

        average_offset = total_offset / len(self.calibration_points)
        print(f"📊 Average offset: {average_offset:.1f} pixels")
        print(
            f"📈 Calibration quality: {'Excellent' if average_offset < 10 else 'Good' if average_offset < 25 else 'Needs improvement'}")


def main():
    """Main function to run the enhanced visual calibration tool"""
    try:
        calibrator = VisualDolphinCalibrator()

        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            print("\n✅ Enhanced calibration completed successfully!")
            print("💡 9 points provide much better accuracy across the screen")
        else:
            print("\n❌ Calibration failed or was cancelled")

    except Exception as e:
        print(f"\n💥 Error during calibration: {e}")
        import traceback
        traceback.print_exc()

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()