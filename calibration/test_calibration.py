import json
import os
import tkinter as tk
import win32gui
import win32api
import time
import threading
from typing import List, Tuple, Optional

from src.utils.calibration import CalibrationUtils


class WiimoteDisplay:
    def __init__(self, calibration_file: str = os.path.join("../game_files", "calibration.json")):
        # Initialize CalibrationUtils
        try:
            self.calibrator = CalibrationUtils(calibration_file)
        except (FileNotFoundError, ValueError) as e:
            raise e

        print(f"📊 Loaded calibration points:")
        for point in self.calibrator.points:
            mx, my = point["mouse"]["x"], point["mouse"]["y"]
            wx, wy = point["wiimote"]["x"], point["wiimote"]["y"]
            print(f"   P{point['point_number']}: Mouse({mx}, {my}) → Wiimote({wx}, {wy})")

        # Test transformation with first calibration point
        test_point = self.calibrator.points[0]
        test_mx, test_my = test_point["mouse"]["x"], test_point["mouse"]["y"]
        test_wx, test_wy = self.calibrator.conversion(test_mx, test_my)
        expected_wx, expected_wy = test_point["wiimote"]["x"], test_point["wiimote"]["y"]
        print(
            f"🧪 Transform test: Mouse({test_mx}, {test_my}) → Wiimote({test_wx:.1f}, {test_wy:.1f}) [Expected: ({expected_wx}, {expected_wy})]")

        # Find Dolphin window
        self.dolphin_hwnd = self._find_dolphin_window()

        # Get Dolphin window dimensions
        self.window_width, self.window_height = self._get_dolphin_window_size()

        # Initialize GUI with Dolphin window size
        self.root = tk.Tk()
        self.root.title("Wiimote Position Display")
        self.root.geometry(f"{self.window_width + 20}x{self.window_height + 80}")
        self.root.configure(bg='black')

        # Create display canvas with same size as Dolphin window
        self.canvas = tk.Canvas(self.root, width=self.window_width, height=self.window_height,
                                bg='darkblue', highlightthickness=0)
        self.canvas.pack(pady=10)

        # Info label
        self.info_label = tk.Label(self.root, text="Move mouse over Dolphin window",
                                   fg='white', bg='black', font=('Arial', 10))
        self.info_label.pack()

        # Mouse cursor (blue circle)
        self.cursor_size = 8
        self.mouse_cursor = self.canvas.create_oval(0, 0, self.cursor_size, self.cursor_size,
                                                    fill='blue', outline='white', width=2)

        # Wiimote cursor (red circle)
        self.wiimote_cursor = self.canvas.create_oval(0, 0, self.cursor_size, self.cursor_size,
                                                      fill='red', outline='white', width=2)

        # Crosshair lines for mouse (blue)
        self.mouse_h_line = self.canvas.create_line(0, 0, self.window_width, 0, fill='lightblue', dash=(3, 3))
        self.mouse_v_line = self.canvas.create_line(0, 0, 0, self.window_height, fill='lightblue', dash=(3, 3))

        # Crosshair lines for wiimote (red)
        self.wiimote_h_line = self.canvas.create_line(0, 0, self.window_width, 0, fill='lightcoral', dash=(3, 3))
        self.wiimote_v_line = self.canvas.create_line(0, 0, 0, self.window_height, fill='lightcoral', dash=(3, 3))

        # Calibration points display
        self._draw_calibration_points()

        # Add click test functionality
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Start position tracking
        self.running = True
        self.tracking_thread = threading.Thread(target=self._track_position, daemon=True)
        self.tracking_thread.start()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _find_dolphin_window(self) -> Optional[int]:
        """Find Dolphin window handle with user selection"""

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
            return None

        if len(windows) == 1:
            hwnd, title = windows[0]
            print(f"✅ Found Dolphin window: {title}")
            return hwnd

        # Multiple windows found, let user choose
        print("🔍 Multiple windows found:")
        for i, (hwnd, title) in enumerate(windows):
            print(f"   {i + 1}. {title}")

        while True:
            try:
                choice = int(input("Select window number: ")) - 1
                if 0 <= choice < len(windows):
                    hwnd, title = windows[choice]
                    print(f"✅ Selected: {title}")
                    return hwnd
                else:
                    print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")

    def _get_dolphin_window_size(self) -> Tuple[int, int]:
        """Get the client area size of the Dolphin window"""
        if not self.dolphin_hwnd:
            print("⚠️ No Dolphin window found, using default size")
            return 640, 480

        try:
            client_rect = win32gui.GetClientRect(self.dolphin_hwnd)
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]
            print(f"📐 Dolphin window size: {width}x{height}")
            return width, height
        except Exception as e:
            print(f"⚠️ Error getting window size: {e}, using default")
            return 640, 480

    def _get_window_coordinates(self, x: int, y: int) -> Tuple[int, int]:
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

    def _is_mouse_in_dolphin(self) -> bool:
        """Check if mouse is in Dolphin window"""
        if not self.dolphin_hwnd:
            return False

        cursor_pos = win32gui.GetCursorPos()
        hwnd = win32gui.WindowFromPoint(cursor_pos)
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def _draw_calibration_points(self):
        """Draw calibration points on canvas"""
        # Get wiimote coordinate bounds for scaling
        wiimote_points = [(p["wiimote"]["x"], p["wiimote"]["y"]) for p in self.calibrator.points]
        min_x = min(p[0] for p in wiimote_points)
        max_x = max(p[0] for p in wiimote_points)
        min_y = min(p[1] for p in wiimote_points)
        max_y = max(p[1] for p in wiimote_points)

        # Add padding
        padding = 20
        scale_x = (self.window_width - 2 * padding) / (max_x - min_x) if max_x != min_x else 1
        scale_y = (self.window_height - 2 * padding) / (max_y - min_y) if max_y != min_y else 1

        for i, point in enumerate(self.calibrator.points):
            wx, wy = point["wiimote"]["x"], point["wiimote"]["y"]

            # Scale to canvas coordinates
            canvas_x = padding + (wx - min_x) * scale_x
            canvas_y = padding + (wy - min_y) * scale_y

            # Draw calibration point
            self.canvas.create_oval(canvas_x - 3, canvas_y - 3, canvas_x + 3, canvas_y + 3,
                                    fill='yellow', outline='orange', width=1)
            self.canvas.create_text(canvas_x + 10, canvas_y - 10, text=f"P{i + 1}",
                                    fill='yellow', font=('Arial', 8))

        # Store scaling info for cursor positioning
        self.scale_info = {
            'min_x': min_x, 'max_x': max_x,
            'min_y': min_y, 'max_y': max_y,
            'scale_x': scale_x, 'scale_y': scale_y,
            'padding': padding
        }

    def _mouse_to_canvas_coordinates(self, mouse_x: float, mouse_y: float) -> Tuple[float, float]:
        """Convert mouse coordinates to canvas coordinates (1:1 since canvas matches window size)"""
        # Since canvas is now the same size as Dolphin window, mouse coordinates map directly
        return mouse_x, mouse_y

    def _update_mouse_cursor(self, mouse_x: float, mouse_y: float):
        """Update mouse cursor position on canvas"""
        canvas_x, canvas_y = self._mouse_to_canvas_coordinates(mouse_x, mouse_y)

        # Clamp to canvas bounds
        canvas_x = max(0, min(self.window_width, canvas_x))
        canvas_y = max(0, min(self.window_height, canvas_y))

        # Update mouse cursor position
        self.canvas.coords(self.mouse_cursor,
                           canvas_x - self.cursor_size // 2,
                           canvas_y - self.cursor_size // 2,
                           canvas_x + self.cursor_size // 2,
                           canvas_y + self.cursor_size // 2)

        # Update mouse crosshair
        self.canvas.coords(self.mouse_h_line, 0, canvas_y, self.window_width, canvas_y)
        self.canvas.coords(self.mouse_v_line, canvas_x, 0, canvas_x, self.window_height)

    def _update_cursor_position(self, wiimote_x: float, wiimote_y: float):
        """Update wiimote cursor position on canvas"""
        info = self.scale_info

        # Scale to canvas coordinates
        canvas_x = info['padding'] + (wiimote_x - info['min_x']) * info['scale_x']
        canvas_y = info['padding'] + (wiimote_y - info['min_y']) * info['scale_y']

        # Clamp to canvas bounds
        canvas_x = max(0, min(self.window_width, canvas_x))
        canvas_y = max(0, min(self.window_height, canvas_y))

        # Update wiimote cursor position
        self.canvas.coords(self.wiimote_cursor,
                           canvas_x - self.cursor_size // 2,
                           canvas_y - self.cursor_size // 2,
                           canvas_x + self.cursor_size // 2,
                           canvas_y + self.cursor_size // 2)

        # Update wiimote crosshair
        self.canvas.coords(self.wiimote_h_line, 0, canvas_y, self.window_width, canvas_y)
        self.canvas.coords(self.wiimote_v_line, canvas_x, 0, canvas_x, self.window_height)

    def _track_position(self):
        """Track mouse position and update display"""
        last_debug_time = 0

        while self.running:
            try:
                current_time = time.time()

                # Get current mouse position
                cursor_pos = win32gui.GetCursorPos()

                if self._is_mouse_in_dolphin():
                    # Get mouse position relative to window
                    mouse_x, mouse_y = self._get_window_coordinates(*cursor_pos)

                    # Transform to wiimote coordinates using CalibrationUtils
                    wiimote_x, wiimote_y = self.calibrator.conversion(mouse_x, mouse_y)

                    # Update both displays
                    self.root.after(0, self._update_mouse_cursor, mouse_x, mouse_y)
                    self.root.after(0, self._update_cursor_position, wiimote_x, wiimote_y)
                    self.root.after(0, lambda: self.info_label.config(
                        text=f"Mouse: ({mouse_x}, {mouse_y}) → Wiimote: ({wiimote_x:.1f}, {wiimote_y:.1f})"))

                    # Debug output every 2 seconds
                    if current_time - last_debug_time > 2:
                        print(f"🐭 Mouse: ({mouse_x}, {mouse_y}) → Wiimote: ({wiimote_x:.1f}, {wiimote_y:.1f})")
                        last_debug_time = current_time

                else:
                    # Mouse not in Dolphin window
                    self.root.after(0, lambda: self.info_label.config(text="Move mouse over Dolphin window"))

                    # Debug output every 5 seconds when not in window
                    if current_time - last_debug_time > 5:
                        hwnd_at_cursor = win32gui.WindowFromPoint(cursor_pos)
                        window_title = win32gui.GetWindowText(hwnd_at_cursor) if hwnd_at_cursor else "None"
                        print(f"🔍 Mouse at ({cursor_pos[0]}, {cursor_pos[1]}) - Window: {window_title}")
                        last_debug_time = current_time

                time.sleep(0.016)  # ~60 FPS

            except Exception as e:
                print(f"❌ Error in position tracking: {e}")
                time.sleep(0.1)

    def _on_canvas_click(self, event):
        """Handle click on canvas for testing"""
        # Convert canvas coordinates back to wiimote coordinates
        info = self.scale_info

        # Convert from canvas to wiimote coordinates
        wiimote_x = info['min_x'] + (event.x - info['padding']) / info['scale_x']
        wiimote_y = info['min_y'] + (event.y - info['padding']) / info['scale_y']

        # Convert back to mouse coordinates using inverse transformation
        mouse_x, mouse_y = self.calibrator.inverse_conversion(wiimote_x, wiimote_y)

        print(f"🖱️ Canvas click test:")
        print(f"   Canvas({event.x}, {event.y}) → Wiimote({wiimote_x:.1f}, {wiimote_y:.1f})")
        print(f"   Wiimote({wiimote_x:.1f}, {wiimote_y:.1f}) → Mouse({mouse_x:.1f}, {mouse_y:.1f})")

        # Update both cursors to clicked position
        self._update_mouse_cursor(mouse_x, mouse_y)
        self._update_cursor_position(wiimote_x, wiimote_y)

    def _on_closing(self):
        """Handle window close event"""
        self.running = False
        self.root.destroy()

    def run(self):
        """Start the display"""
        print(f"\n🎮 Wiimote Position Display")
        print(f"📊 Loaded {len(self.calibrator.points)} calibration points")
        print(f"🎯 Move your mouse over the Dolphin window to see both positions:")
        print(f"   🔵 Blue cursor = Mouse position")
        print(f"   🔴 Red cursor = Wiimote position")
        print(f"🖱️ Click anywhere on the blue canvas to test coordinates")
        print(f"❌ Close the window to exit")
        print(f"\n💡 Debug info will be printed every 2 seconds when mouse is in Dolphin")

        self.root.mainloop()


def main():
    """Main function"""
    try:
        display = WiimoteDisplay()
        display.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()