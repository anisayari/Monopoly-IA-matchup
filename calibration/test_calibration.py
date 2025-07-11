import os
import time
import threading
import tkinter as tk
import win32gui
import win32api
from typing import Optional, Tuple
from src.utils.calibration import CalibrationUtils


class WiimoteDisplay:
    def __init__(self, calibration_file: str = os.path.join("../game_files", "calibration.json")):
        # Load calibration data and setup transformer
        self.calibration = CalibrationUtils(calibration_file)
        print(f"📊 Loaded {len(self.calibration.points)} calibration points")

        # Find Dolphin window
        self.dolphin_hwnd = self._find_dolphin_window()

        # Setup GUI
        self._setup_gui()

        # Start position tracking
        self.running = True
        self.tracking_thread = threading.Thread(target=self._track_position, daemon=True)
        self.tracking_thread.start()

    def _find_dolphin_window(self) -> Optional[int]:
        """Find Dolphin window handle"""

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if "dolphin" in window_text.lower() or "monopoly" in window_text.lower():
                    windows.append((hwnd, window_text))

        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)

        if not windows:
            print("❌ No Dolphin window found!")
            return None

        if len(windows) == 1:
            hwnd, title = windows[0]
            print(f"✅ Found Dolphin window: {title}")
            return hwnd

        # Multiple windows - let user choose
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
                print("❌ Invalid choice, try again")
            except ValueError:
                print("❌ Please enter a valid number")

    def _setup_gui(self):
        """Initialize the GUI"""
        self.root = tk.Tk()
        self.root.title("Wiimote Position Display")
        self.root.geometry("400x300")
        self.root.configure(bg='black')

        # Canvas for display
        self.canvas = tk.Canvas(self.root, width=380, height=250, bg='darkblue', highlightthickness=0)
        self.canvas.pack(pady=10)

        # Info label
        self.info_label = tk.Label(self.root, text="Move mouse over Dolphin window",
                                   fg='white', bg='black', font=('Arial', 10))
        self.info_label.pack()

        # Wiimote cursor
        self.cursor_size = 8
        self.cursor = self.canvas.create_oval(0, 0, self.cursor_size, self.cursor_size,
                                              fill='red', outline='white', width=2)

        # Crosshair lines
        self.h_line = self.canvas.create_line(0, 0, 380, 0, fill='gray', dash=(3, 3))
        self.v_line = self.canvas.create_line(0, 0, 0, 250, fill='gray', dash=(3, 3))

        # Draw calibration points and setup scaling
        self._setup_display_scaling()

        # Event handlers
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_display_scaling(self):
        """Setup coordinate scaling for display and draw calibration points"""
        canvas_width, canvas_height = 380, 250
        padding = 20

        # Get wiimote coordinate bounds
        wiimote_points = [(p["wiimote"]["x"], p["wiimote"]["y"]) for p in self.calibration.points]
        min_x, max_x = min(p[0] for p in wiimote_points), max(p[0] for p in wiimote_points)
        min_y, max_y = min(p[1] for p in wiimote_points), max(p[1] for p in wiimote_points)

        # Calculate scaling factors
        scale_x = (canvas_width - 2 * padding) / (max_x - min_x) if max_x != min_x else 1
        scale_y = (canvas_height - 2 * padding) / (max_y - min_y) if max_y != min_y else 1

        # Store scaling info
        self.scale_info = {
            'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y,
            'scale_x': scale_x, 'scale_y': scale_y, 'padding': padding
        }

        # Draw calibration points
        for i, point in enumerate(self.calibration.points):
            wx, wy = point["wiimote"]["x"], point["wiimote"]["y"]
            canvas_x = padding + (wx - min_x) * scale_x
            canvas_y = padding + (wy - min_y) * scale_y

            self.canvas.create_oval(canvas_x - 3, canvas_y - 3, canvas_x + 3, canvas_y + 3,
                                    fill='yellow', outline='orange', width=1)
            self.canvas.create_text(canvas_x + 10, canvas_y - 10, text=f"P{i + 1}",
                                    fill='yellow', font=('Arial', 8))

    def _get_window_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Convert screen coordinates to window-relative coordinates"""
        if not self.dolphin_hwnd:
            return x, y

        window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
        client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

        border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
        title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

        return x - window_rect[0] - border_x, y - window_rect[1] - title_height

    def _is_mouse_in_dolphin(self) -> bool:
        """Check if mouse is in Dolphin window"""
        if not self.dolphin_hwnd:
            return False
        cursor_pos = win32gui.GetCursorPos()
        hwnd = win32gui.WindowFromPoint(cursor_pos)
        return hwnd == self.dolphin_hwnd or win32gui.GetParent(hwnd) == self.dolphin_hwnd

    def _update_cursor_position(self, wiimote_x: float, wiimote_y: float):
        """Update cursor position on canvas"""
        info = self.scale_info

        # Scale to canvas coordinates
        canvas_x = info['padding'] + (wiimote_x - info['min_x']) * info['scale_x']
        canvas_y = info['padding'] + (wiimote_y - info['min_y']) * info['scale_y']

        # Clamp to canvas bounds
        canvas_x = max(0, min(380, canvas_x))
        canvas_y = max(0, min(250, canvas_y))

        # Update cursor and crosshair
        half_size = self.cursor_size // 2
        self.canvas.coords(self.cursor, canvas_x - half_size, canvas_y - half_size,
                           canvas_x + half_size, canvas_y + half_size)
        self.canvas.coords(self.h_line, 0, canvas_y, 380, canvas_y)
        self.canvas.coords(self.v_line, canvas_x, 0, canvas_x, 250)

        # Update info label
        self.info_label.config(text=f"Wiimote: ({wiimote_x:.1f}, {wiimote_y:.1f})")

    def _track_position(self):
        """Track mouse position and update display"""
        last_debug_time = 0

        while self.running:
            try:
                current_time = time.time()
                cursor_pos = win32gui.GetCursorPos()

                if self._is_mouse_in_dolphin():
                    # Transform coordinates
                    mouse_x, mouse_y = self._get_window_coordinates(*cursor_pos)
                    wiimote_x, wiimote_y = self.calibration.conversion(mouse_x, mouse_y)

                    # Update display
                    self.root.after(0, self._update_cursor_position, wiimote_x, wiimote_y)

                    # Debug output every 2 seconds
                    if current_time - last_debug_time > 2:
                        print(f"🐭 Mouse: ({mouse_x}, {mouse_y}) → Wiimote: ({wiimote_x:.1f}, {wiimote_y:.1f})")
                        last_debug_time = current_time
                else:
                    self.root.after(0, lambda: self.info_label.config(text="Move mouse over Dolphin window"))

                time.sleep(0.016)  # ~60 FPS

            except Exception as e:
                print(f"❌ Error in tracking: {e}")
                time.sleep(0.1)

    def _on_canvas_click(self, event):
        """Handle canvas click for testing"""
        info = self.scale_info
        wiimote_x = info['min_x'] + (event.x - info['padding']) / info['scale_x']
        wiimote_y = info['min_y'] + (event.y - info['padding']) / info['scale_y']
        print(f"🖱️ Canvas click: ({event.x}, {event.y}) → Wiimote({wiimote_x:.1f}, {wiimote_y:.1f})")
        self._update_cursor_position(wiimote_x, wiimote_y)

    def _on_closing(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()

    def run(self):
        """Start the display"""
        print("\n🎮 Wiimote Position Display")
        print("🎯 Move mouse over Dolphin to see Wiimote position")
        print("🖱️ Click canvas to test coordinates")
        print("❌ Close window to exit\n")
        self.root.mainloop()


def main():
    try:
        display = WiimoteDisplay()
        display.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()