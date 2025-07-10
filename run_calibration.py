import os.path

import win32gui
import win32api
import win32con
import time
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class CalibrationPoint:
    """Represents a calibration point with mouse and Wiimote coordinates"""
    mouse_x: int
    mouse_y: int
    wiimote_x: float
    wiimote_y: float
    point_number: int


class DolphinCalibrator:
    def __init__(self):
        self.dolphin_hwnd: Optional[int] = None
        self.calibration_points: List[CalibrationPoint] = []
        self.current_point = 0

    def find_dolphin_window(self) -> bool:
        """Find the Dolphin emulator window"""

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "dolphin" in window_text.lower() or "mario party" in window_text.lower():
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

    def get_window_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to window-relative coordinates"""
        if not self.dolphin_hwnd:
            return x, y

        # Get window position
        window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

        # Calculate title bar and border offsets
        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

        # Convert to window-relative coordinates
        rel_x = x - window_rect[0] - border_x
        rel_y = y - window_rect[1] - title_height

        return rel_x, rel_y

    def is_point_in_dolphin_window(self, x: int, y: int) -> bool:
        """Check if a point is inside the Dolphin window"""
        if not self.dolphin_hwnd:
            return False

        hwnd = win32gui.WindowFromPoint((x, y))
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def wait_for_right_click(self) -> Tuple[int, int]:
        """Wait for a right-click and return the coordinates using polling"""
        print(f"\n🎯 Point {self.current_point + 1}/4")
        print("   Right-click anywhere in the Dolphin window...")
        print("   (The script will detect when you right-click)")

        # Ensure button is not currently pressed
        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            time.sleep(0.01)

        # Track previous right button state
        prev_right_button = False

        while True:
            try:
                # Check right mouse button state
                right_button_down = win32api.GetKeyState(win32con.VK_RBUTTON) < 0

                # Detect right button press (transition from up to down)
                if right_button_down and not prev_right_button:
                    # Get current cursor position
                    cursor_pos = win32gui.GetCursorPos()

                    # Check if click is in Dolphin window
                    if self.is_point_in_dolphin_window(*cursor_pos):
                        # Convert to window coordinates
                        window_coords = self.get_window_coordinates(*cursor_pos)

                        # Wait for button to be released before continuing
                        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
                            time.sleep(0.01)

                        return window_coords

                prev_right_button = right_button_down
                time.sleep(0.01)  # Small delay to prevent high CPU usage

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error checking mouse state: {e}")
                time.sleep(0.1)

    def get_wiimote_coordinates(self) -> Tuple[float, float]:
        """Get Wiimote coordinates by clicking on the corresponding position"""
        print("📍 Now click on the corresponding Wiimote position:")
        print("   (Move your cursor to where the Wiimote cursor should be and right-click)")

        # Ensure button is not currently pressed (wait for previous click to be released)
        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            time.sleep(0.01)

        # Track previous right button state
        prev_right_button = False

        while True:
            try:
                # Check right mouse button state
                right_button_down = win32api.GetKeyState(win32con.VK_RBUTTON) < 0

                # Detect right button press (transition from up to down)
                if right_button_down and not prev_right_button:
                    # Get current cursor position
                    cursor_pos = win32gui.GetCursorPos()

                    # Check if click is in Dolphin window
                    if self.is_point_in_dolphin_window(*cursor_pos):
                        # Convert to window coordinates
                        wiimote_x, wiimote_y = self.get_window_coordinates(*cursor_pos)

                        # Wait for button to be released before continuing
                        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
                            time.sleep(0.01)

                        return float(wiimote_x), float(wiimote_y)

                prev_right_button = right_button_down
                time.sleep(0.01)  # Small delay to prevent high CPU usage

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error checking mouse state: {e}")
                time.sleep(0.1)

    def calibrate(self) -> bool:
        """Main calibration process"""
        print("🎮 Dolphin Screen Calibration Tool")
        print("=" * 40)

        if not self.find_dolphin_window():
            return False

        print("\n📋 Instructions:")
        print("   1. Right-click on a point in the Dolphin window (mouse coordinates)")
        print("   2. Right-click on the corresponding Wiimote cursor position")
        print("   3. Repeat for 4 different point pairs")
        print("   4. Choose points at different areas (corners work well)")
        print("   5. Press Ctrl+C anytime to cancel")

        input("\nPress Enter when ready to start calibration...")

        try:
            for i in range(4):
                self.current_point = i

                # Get mouse coordinates via right-click
                mouse_x, mouse_y = self.wait_for_right_click()
                print(f"✅ Mouse coordinates: ({mouse_x}, {mouse_y})")

                # Get Wiimote coordinates via right-click
                wiimote_x, wiimote_y = self.get_wiimote_coordinates()
                print(f"✅ Wiimote coordinates: ({wiimote_x}, {wiimote_y})")

                # Store calibration point
                point = CalibrationPoint(
                    mouse_x=mouse_x,
                    mouse_y=mouse_y,
                    wiimote_x=wiimote_x,
                    wiimote_y=wiimote_y,
                    point_number=i + 1
                )
                self.calibration_points.append(point)

                print(f"✅ Point {i + 1} saved: Mouse({mouse_x}, {mouse_y}) → Wiimote({wiimote_x}, {wiimote_y})")
                print()  # Add spacing between points

        except KeyboardInterrupt:
            print("\n❌ Calibration cancelled by user")
            return False

        return True

    def save_calibration(self, filename: str = os.path.join("game_files", "calibration.json")) -> None:
        """Save calibration data to JSON file"""
        calibration_data = {
            "window_title": win32gui.GetWindowText(self.dolphin_hwnd) if self.dolphin_hwnd else "Unknown",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
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

        for point in self.calibration_points:
            print(f"Point {point.point_number}:")
            print(f"   Mouse:   ({point.mouse_x:>4}, {point.mouse_y:>4})")
            print(f"   Wiimote: ({point.wiimote_x:>6.1f}, {point.wiimote_y:>6.1f})")
            print()

        # Calculate some basic statistics
        if len(self.calibration_points) >= 2:
            mouse_x_range = max(p.mouse_x for p in self.calibration_points) - min(
                p.mouse_x for p in self.calibration_points)
            mouse_y_range = max(p.mouse_y for p in self.calibration_points) - min(
                p.mouse_y for p in self.calibration_points)
            wiimote_x_range = max(p.wiimote_x for p in self.calibration_points) - min(
                p.wiimote_x for p in self.calibration_points)
            wiimote_y_range = max(p.wiimote_y for p in self.calibration_points) - min(
                p.wiimote_y for p in self.calibration_points)

            print("📊 Coverage:")
            print(f"   Mouse area:   {mouse_x_range} x {mouse_y_range} pixels")
            print(f"   Wiimote area: {wiimote_x_range:.1f} x {wiimote_y_range:.1f} units")

    def create_transformation_functions(self):
        """Create transformation functions for converting between coordinate systems"""
        if len(self.calibration_points) < 2:
            print("❌ Need at least 2 points for transformation")
            return None, None

        # Simple linear transformation (works best with 2 points)
        # For more complex transformations, you'd use multiple points
        p1, p2 = self.calibration_points[0], self.calibration_points[1]

        # Calculate scale factors
        mouse_dx = p2.mouse_x - p1.mouse_x
        mouse_dy = p2.mouse_y - p1.mouse_y
        wiimote_dx = p2.wiimote_x - p1.wiimote_x
        wiimote_dy = p2.wiimote_y - p1.wiimote_y

        if mouse_dx == 0 or mouse_dy == 0:
            print("❌ Invalid calibration points (no movement in one axis)")
            return None, None

        scale_x = wiimote_dx / mouse_dx
        scale_y = wiimote_dy / mouse_dy

        def mouse_to_wiimote(mouse_x, mouse_y):
            """Convert mouse coordinates to Wiimote coordinates"""
            wiimote_x = p1.wiimote_x + (mouse_x - p1.mouse_x) * scale_x
            wiimote_y = p1.wiimote_y + (mouse_y - p1.mouse_y) * scale_y
            return wiimote_x, wiimote_y

        def wiimote_to_mouse(wiimote_x, wiimote_y):
            """Convert Wiimote coordinates to mouse coordinates"""
            mouse_x = p1.mouse_x + (wiimote_x - p1.wiimote_x) / scale_x
            mouse_y = p1.mouse_y + (wiimote_y - p1.wiimote_y) / scale_y
            return int(mouse_x), int(mouse_y)

        print("\n🔧 Transformation functions created!")
        print(f"   Scale factors: X={scale_x:.3f}, Y={scale_y:.3f}")

        return mouse_to_wiimote, wiimote_to_mouse


def main():
    """Main function to run the calibration tool"""
    try:
        calibrator = DolphinCalibrator()

        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()

            # Create transformation functions
            m2w, w2m = calibrator.create_transformation_functions()

            if m2w and w2m:
                print("\n✅ Calibration completed successfully!")
                print("   Transformation functions are ready to use")

                # Test the transformation with the first calibration point
                test_point = calibrator.calibration_points[0]
                converted_x, converted_y = m2w(test_point.mouse_x, test_point.mouse_y)
                print(f"\n🧪 Test conversion:")
                print(
                    f"   Original: Mouse({test_point.mouse_x}, {test_point.mouse_y}) → Wiimote({test_point.wiimote_x}, {test_point.wiimote_y})")
                print(
                    f"   Converted: Mouse({test_point.mouse_x}, {test_point.mouse_y}) → Wiimote({converted_x:.1f}, {converted_y:.1f})")
            else:
                print("\n⚠️ Calibration completed but transformation functions could not be created")
        else:
            print("\n❌ Calibration failed or was cancelled")

    except Exception as e:
        print(f"\n💥 Error during calibration: {e}")
        import traceback
        traceback.print_exc()

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()