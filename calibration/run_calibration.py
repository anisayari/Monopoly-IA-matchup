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
    mouse_x: int
    mouse_y: int
    wiimote_x: float
    wiimote_y: float
    point_number: int


class DolphinCalibrator:
    def __init__(self):
        self.dolphin_hwnd: Optional[int] = None
        self.calibration_points: List[CalibrationPoint] = []

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
            return False

        if len(windows) == 1:
            self.dolphin_hwnd, window_title = windows[0]
            print(f"✅ Found Dolphin window: {window_title}")
            return True

        # Multiple windows found
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
                print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")

    def get_window_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to window-relative coordinates"""
        if not self.dolphin_hwnd:
            return x, y

        window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

        rel_x = x - window_rect[0] - border_x
        rel_y = y - window_rect[1] - title_height

        return rel_x, rel_y

    def is_point_in_dolphin_window(self, x: int, y: int) -> bool:
        """Check if a point is inside the Dolphin window"""
        if not self.dolphin_hwnd:
            return False
        hwnd = win32gui.WindowFromPoint((x, y))
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def wait_for_right_click(self, point_num: int) -> Tuple[int, int]:
        """Wait for a right-click and return the coordinates"""
        print(f"\n🎯 Point {point_num}/4 - Right-click in Dolphin window...")

        # Wait for button release if currently pressed
        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
            time.sleep(0.01)

        prev_right_button = False
        while True:
            try:
                right_button_down = win32api.GetKeyState(win32con.VK_RBUTTON) < 0

                if right_button_down and not prev_right_button:
                    cursor_pos = win32gui.GetCursorPos()
                    if self.is_point_in_dolphin_window(*cursor_pos):
                        window_coords = self.get_window_coordinates(*cursor_pos)
                        # Wait for button release
                        while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
                            time.sleep(0.01)
                        return window_coords

                prev_right_button = right_button_down
                time.sleep(0.01)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.1)

    def calibrate(self) -> bool:
        """Main calibration process"""
        print("🎮 Dolphin Screen Calibration Tool")
        print("=" * 40)

        if not self.find_dolphin_window():
            return False

        print("\n📋 Instructions:")
        print("   1. Right-click on a point in Dolphin (mouse coordinates)")
        print("   2. Right-click on corresponding Wiimote cursor position")
        print("   3. Repeat for 4 different point pairs")
        print("   4. Choose points at different areas (corners work well)")

        input("\nPress Enter when ready...")

        try:
            for i in range(4):
                # Get mouse coordinates
                mouse_x, mouse_y = self.wait_for_right_click(i + 1)
                print(f"✅ Mouse: ({mouse_x}, {mouse_y})")

                # Get Wiimote coordinates
                print("📍 Now click corresponding Wiimote position...")
                wiimote_x, wiimote_y = self.wait_for_right_click(i + 1)
                print(f"✅ Wiimote: ({wiimote_x}, {wiimote_y})")

                # Store point
                point = CalibrationPoint(mouse_x, mouse_y, float(wiimote_x), float(wiimote_y), i + 1)
                self.calibration_points.append(point)
                print(f"✅ Point {i + 1} saved\n")

        except KeyboardInterrupt:
            print("\n❌ Calibration cancelled")
            return False

        return True

    def save_calibration(self, filename: str = os.path.join("../game_files", "calibration.json")):
        """Save calibration data to JSON file"""
        data = {
            "window_title": win32gui.GetWindowText(self.dolphin_hwnd) if self.dolphin_hwnd else "Unknown",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "points": [
                {
                    "point_number": p.point_number,
                    "mouse": {"x": p.mouse_x, "y": p.mouse_y},
                    "wiimote": {"x": p.wiimote_x, "y": p.wiimote_y}
                }
                for p in self.calibration_points
            ]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Calibration saved to {filename}")

    def display_results(self):
        """Display calibration results"""
        print("\n🎯 Calibration Results:")
        print("=" * 50)

        for point in self.calibration_points:
            print(f"Point {point.point_number}: Mouse({point.mouse_x:>4}, {point.mouse_y:>4}) → "
                  f"Wiimote({point.wiimote_x:>6.1f}, {point.wiimote_y:>6.1f})")


def main():
    try:
        calibrator = DolphinCalibrator()

        if calibrator.calibrate():
            calibrator.display_results()
            calibrator.save_calibration()
            print("\n✅ Calibration completed successfully!")
        else:
            print("\n❌ Calibration failed or was cancelled")

    except Exception as e:
        print(f"\n💥 Error: {e}")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()