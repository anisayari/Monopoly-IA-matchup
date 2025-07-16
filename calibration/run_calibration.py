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
        # Reorder corners for better perspective transform (clockwise from top-left)
        self.corner_names = ["upper left", "upper right", "lower right", "lower left"]

    def find_dolphin_window(self) -> bool:
        """Find the Dolphin emulator window"""

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "dolphin" in window_text.lower():
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

    def get_corner_coordinates(self, corner_index: int) -> Tuple[int, int]:
        """Get the coordinates of window corners based on actual window rect"""
        if not self.dolphin_hwnd:
            return 0, 0

        # Get actual client area dimensions
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
        width = client_rect[2] - client_rect[0]
        height = client_rect[3] - client_rect[1]

        # Clockwise ordering starting from top-left
        corners = [
            (0, 0),  # upper left
            (width, 0),  # upper right
            (width, height),  # lower right
            (0, height)  # lower left
        ]

        return corners[corner_index]

    def is_point_in_dolphin_window(self, x: int, y: int) -> bool:
        """Check if a point is inside the Dolphin window"""
        if not self.dolphin_hwnd:
            return False

        hwnd = win32gui.WindowFromPoint((x, y))
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def wait_for_click(self, corner_name: str, corner_x: int, corner_y: int) -> Tuple[int, int]:
        """Wait for a right-click and return the coordinates"""
        print(f"\n🎯 Point {self.current_point + 1}/4: {corner_name}")
        print(f"   Target corner: ({corner_x}, {corner_y})")
        print(f"   1. Align your Wiimote to point at the {corner_name} corner")
        print("   2. Right-click anywhere in the Dolphin window")
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

    def calibrate(self) -> bool:
        """Main calibration process"""
        print("🎮 Dolphin Screen Calibration Tool")
        print("=" * 40)

        if not self.find_dolphin_window():
            return False

        print("\n📋 Instructions:")
        print("   1. Point your Wiimote at the specified corner")
        print("   2. Right-click anywhere in the Dolphin window")
        print("   3. Repeat for all 4 corners in clockwise order")
        print("   4. Press Ctrl+C anytime to cancel")
        print("\n💡 Important: Click precisely where your Wiimote cursor appears!")

        input("\nPress Enter when ready to start calibration...")

        try:
            for i in range(4):
                self.current_point = i
                corner_name = self.corner_names[i]

                # Get actual corner coordinates (target position)
                corner_x, corner_y = self.get_corner_coordinates(i)

                # Get where user clicked when pointing at corner
                click_x, click_y = self.wait_for_click(corner_name, corner_x, corner_y)
                print(f"✅ Clicked at: ({click_x}, {click_y}) when pointing at {corner_name}")

                # Store calibration point with CORRECT mapping:
                # mouse = where user clicked
                # wiimote = target corner position
                point = CalibrationPoint(
                    mouse_x=click_x,  # Where user clicked
                    mouse_y=click_y,
                    wiimote_x=float(corner_x),  # Target corner
                    wiimote_y=float(corner_y),
                    point_number=i + 1
                )
                self.calibration_points.append(point)

                print(f"✅ Point {i + 1} saved: Click({click_x}, {click_y}) → Corner({corner_x}, {corner_y})")
                print()  # Add spacing between points

        except KeyboardInterrupt:
            print("\n❌ Calibration cancelled by user")
            return False

        return True

    def save_calibration(self, filename: str = os.path.join("../game_files", "calibration.json")) -> None:
        """Save calibration data to JSON file"""

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        calibration_data = {
            "window_title": win32gui.GetWindowText(self.dolphin_hwnd) if self.dolphin_hwnd else "Unknown",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "window_size": {
                "width": win32gui.GetClientRect(self.dolphin_hwnd)[2] if self.dolphin_hwnd else 0,
                "height": win32gui.GetClientRect(self.dolphin_hwnd)[3] if self.dolphin_hwnd else 0
            },
            "points": [
                {
                    "point_number": point.point_number,
                    "mouse": {"x": point.mouse_x, "y": point.mouse_y},  # Where user clicked
                    "wiimote": {"x": point.wiimote_x, "y": point.wiimote_y}  # Target corner
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

            # Calculate offset
            offset_x = abs(point.mouse_x - point.wiimote_x)
            offset_y = abs(point.mouse_y - point.wiimote_y)
            offset_distance = (offset_x ** 2 + offset_y ** 2) ** 0.5
            print(f"   Offset: {offset_distance:.1f} pixels")
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
            print(f"   Click area:   {mouse_x_range} x {mouse_y_range} pixels")
            print(f"   Target area:  {wiimote_x_range:.1f} x {wiimote_y_range:.1f} pixels")

            # Calculate average offset
            avg_offset = sum((p.mouse_x - p.wiimote_x) ** 2 + (p.mouse_y - p.wiimote_y) ** 2
                             for p in self.calibration_points) ** 0.5 / len(self.calibration_points)
            print(f"   Average offset: {avg_offset:.1f} pixels")


def main():
    """Main function to run the calibration tool"""
    try:
        calibrator = DolphinCalibrator()

        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            print("\n✅ Calibration completed successfully!")
            print("💡 Now run the test script to verify accuracy")
        else:
            print("\n❌ Calibration failed or was cancelled")

    except Exception as e:
        print(f"\n💥 Error during calibration: {e}")
        import traceback
        traceback.print_exc()

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()