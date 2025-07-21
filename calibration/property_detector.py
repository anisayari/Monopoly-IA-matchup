import tkinter as tk
from tkinter import ttk, messagebox
import win32gui
import win32api
import win32con
import json
import time
import threading
import ctypes
from ctypes import wintypes
import os
from datetime import datetime

class PersistentPropertyDetector:
    def __init__(self):
        self.dolphin_hwnd = None
        self.overlay = None
        self.control_window = None
        self.canvas = None
        self.summary_text = None
        self.listbox = None
        self.monopoly_data = {}
        self.tracking = False
        self.filename = "../game_files/MonopolyProperties.json"

    def load_monopoly_properties(self):
        """Load MonopolyProperties.json with existing coordinates"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.monopoly_data = json.load(f)

                properties = self.monopoly_data.get('properties', [])
                coordinates_count = sum(1 for p in properties if 'coordinates' in p)

                print(f"✅ Loaded {len(properties)} properties from {self.filename}")
                print(f"📍 {coordinates_count} properties already have coordinates")
                return True
            else:
                print(f"❌ {self.filename} not found!")
                return False
        except Exception as e:
            print(f"❌ Error loading properties: {e}")
            return False

    def save_properties(self):
        """Save the monopoly data back to JSON file"""
        try:
            info = self.get_window_info()

            # Update timestamp and window info
            if 'properties' in self.monopoly_data:
                for prop in self.monopoly_data['properties']:
                    if 'coordinates' in prop:
                        prop['coordinates']['window_size'] = {
                            'width': info['width'] if info else 0,
                            'height': info['height'] if info else 0
                        }
                        prop['coordinates']['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.monopoly_data, f, indent=2, ensure_ascii=False)

            coordinates_count = sum(1 for p in self.monopoly_data.get('properties', []) if 'coordinates' in p)
            print(f"💾 Auto-saved {coordinates_count} property coordinates")

        except Exception as e:
            print(f"❌ Save error: {e}")

    def find_dolphin_window(self):
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and "dolphin" in title.lower():
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect[2] - rect[0] > 200 and rect[3] - rect[1] > 150:
                            windows.append((hwnd, title))
                    except:
                        pass

        windows = []
        win32gui.EnumWindows(enum_callback, windows)

        if not windows:
            print("❌ No Dolphin windows found!")
            return False

        if len(windows) == 1:
            self.dolphin_hwnd = windows[0][0]
            print(f"✅ Found: {windows[0][1]}")
            return True

        print("🔍 Dolphin windows:")
        for i, (_, title) in enumerate(windows):
            print(f"   {i + 1}. {title}")

        while True:
            try:
                choice = int(input("Select: ")) - 1
                if 0 <= choice < len(windows):
                    self.dolphin_hwnd = windows[choice][0]
                    print(f"✅ Selected: {windows[choice][1]}")
                    return True
            except ValueError:
                pass
            print("Invalid choice")

    def get_window_info(self):
        try:
            if not win32gui.IsWindow(self.dolphin_hwnd):
                return None

            window_rect = win32gui.GetWindowRect(self.dolphin_hwnd)
            client_rect = win32gui.GetClientRect(self.dolphin_hwnd)

            border_x = (window_rect[2] - window_rect[0] - client_rect[2]) // 2
            title_height = window_rect[3] - window_rect[1] - client_rect[3] - border_x

            return {
                'left': window_rect[0] + border_x,
                'top': window_rect[1] + title_height,
                'width': client_rect[2],
                'height': client_rect[3]
            }
        except:
            return None

    def screen_to_window(self, screen_x, screen_y):
        info = self.get_window_info()
        if not info:
            return 0, 0
        return screen_x - info['left'], screen_y - info['top']

    def window_to_percent(self, x, y):
        info = self.get_window_info()
        if not info or info['width'] == 0 or info['height'] == 0:
            return 0.0, 0.0
        return (x / info['width']) * 100, (y / info['height']) * 100

    def percent_to_window(self, percent_x, percent_y):
        info = self.get_window_info()
        if not info:
            return 0, 0
        return int(percent_x * info['width'] / 100), int(percent_y * info['height'] / 100)

    def is_click_in_dolphin(self, screen_x, screen_y):
        info = self.get_window_info()
        if not info:
            return False

        return (info['left'] <= screen_x <= info['left'] + info['width'] and
                info['top'] <= screen_y <= info['top'] + info['height'])

    def create_control_window(self):
        self.control_window = tk.Tk()
        self.control_window.title("Monopoly Property Manager")
        self.control_window.geometry("350x600+50+50")
        self.control_window.configure(bg='#2b2b2b')
        self.control_window.attributes('-topmost', True)

        main_frame = tk.Frame(self.control_window, bg='#2b2b2b', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # Title
        title_label = tk.Label(main_frame, text="🏠 Monopoly Properties",
                               fg='#00ff00', bg='#2b2b2b', font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        # Instructions
        inst_label = tk.Label(main_frame, text="Right-click in Dolphin to mark properties",
                              fg='white', bg='#2b2b2b', font=('Arial', 9))
        inst_label.pack(pady=(0, 10))

        # Stats
        properties = self.monopoly_data.get('properties', [])
        total_count = len(properties)
        marked_count = sum(1 for p in properties if 'coordinates' in p)

        stats_label = tk.Label(main_frame, text=f"📊 {marked_count}/{total_count} properties marked",
                               fg='yellow', bg='#2b2b2b', font=('Arial', 10, 'bold'))
        stats_label.pack(pady=(0, 10))

        # Action buttons frame
        btn_frame = tk.Frame(main_frame, bg='#2b2b2b')
        btn_frame.pack(fill='x', pady=(0, 10))

        btn_style = {'font': ('Arial', 9), 'width': 10, 'height': 1}

        tk.Button(btn_frame, text="Save", bg='#66bb6a', fg='white',
                  command=self.manual_save, **btn_style).grid(row=0, column=0, padx=2, pady=2)

        tk.Button(btn_frame, text="Clear All", bg='#ffa726', fg='white',
                  command=self.clear_all_coordinates, **btn_style).grid(row=0, column=1, padx=2, pady=2)

        tk.Button(btn_frame, text="Quit", bg='#ef5350', fg='white',
                  command=self.quit, **btn_style).grid(row=1, column=0, columnspan=2, padx=2, pady=2)

        # Property list section
        list_label = tk.Label(main_frame, text="📋 Properties:",
                              fg='#00ff00', bg='#2b2b2b', font=('Arial', 10, 'bold'))
        list_label.pack(anchor='w', pady=(10, 5))

        # Listbox with scrollbar
        list_frame = tk.Frame(main_frame, bg='#1e1e1e', relief='sunken', bd=1)
        list_frame.pack(fill='both', expand=True)

        self.listbox = tk.Listbox(list_frame, bg='#1e1e1e', fg='white',
                                  font=('Consolas', 9), selectmode=tk.SINGLE)
        list_scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=list_scrollbar.set)

        self.listbox.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')

        # Delete button
        delete_btn = tk.Button(main_frame, text="🗑️ Remove Coordinates", bg='#f44336', fg='white',
                               font=('Arial', 9), command=self.delete_selected_coordinates)
        delete_btn.pack(pady=(5, 0))

        # Summary section
        summary_label = tk.Label(main_frame, text="📊 Details:",
                                 fg='#00ff00', bg='#2b2b2b', font=('Arial', 10, 'bold'))
        summary_label.pack(anchor='w', pady=(10, 5))

        # Summary text area
        summary_frame = tk.Frame(main_frame, bg='#1e1e1e', relief='sunken', bd=1)
        summary_frame.pack(fill='x')

        self.summary_text = tk.Text(summary_frame, bg='#1e1e1e', fg='white',
                                    font=('Consolas', 8), wrap=tk.WORD,
                                    height=6, state=tk.DISABLED)

        summary_scrollbar = tk.Scrollbar(summary_frame, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)

        self.summary_text.pack(side='left', fill='both', expand=True)
        summary_scrollbar.pack(side='right', fill='y')

        # Bind listbox selection
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        self.update_property_list()

    def create_overlay(self):
        self.overlay = tk.Tk()
        self.overlay.title("Property Viewer")
        self.overlay.attributes('-alpha', 0.3)
        self.overlay.attributes('-topmost', True)
        self.overlay.overrideredirect(True)
        self.overlay.configure(bg='black')

        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, bg='black')
        self.canvas.pack(fill='both', expand=True)

        # Make overlay click-through for left clicks
        self.overlay.update()
        hwnd = int(self.overlay.wm_frame(), 16)

        # Get current window style
        style = ctypes.windll.user32.GetWindowLongW(hwnd, win32con.GWL_EXSTYLE)

        # Add transparent flag to make clicks pass through
        style |= 0x00000020  # WS_EX_TRANSPARENT

        # Apply the new style
        ctypes.windll.user32.SetWindowLongW(hwnd, win32con.GWL_EXSTYLE, style)

        self.update_overlay()
        self.start_click_detection()

    def update_overlay(self):
        info = self.get_window_info()
        if info and self.tracking:
            self.overlay.geometry(f"{info['width']}x{info['height']}+{info['left']}+{info['top']}")
            self.canvas.configure(width=info['width'], height=info['height'])
            self.redraw_markers()
            self.overlay.after(100, self.update_overlay)

    def redraw_markers(self):
        self.canvas.delete("all")

        properties = self.monopoly_data.get('properties', [])
        for i, prop in enumerate(properties):
            if 'coordinates' in prop:
                coords = prop['coordinates']
                x, y = self.percent_to_window(coords['x_relative'] * 100, coords['y_relative'] * 100)

                # Different colors for different types
                color = 'lime'
                if prop.get('type') == 'station':
                    color = 'cyan'
                elif prop.get('type') == 'utility':
                    color = 'yellow'

                circle = self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8,
                                                 fill=color, outline='white', width=2)

                number = self.canvas.create_text(x, y, text=str(i + 1),
                                                 fill='black', font=('Arial', 10, 'bold'))

                # Property name with background
                display_name = prop['name'][:15] + "..." if len(prop['name']) > 15 else prop['name']
                name_width = len(display_name) * 7
                name_bg = self.canvas.create_rectangle(x + 12, y - 8, x + 12 + name_width, y + 8,
                                                       fill='white', outline='black')

                name_text = self.canvas.create_text(x + 15, y, text=display_name,
                                                    fill='black', font=('Arial', 9), anchor='w')

    def start_click_detection(self):
        def detector():
            prev_button = False

            while self.tracking:
                try:
                    button_down = win32api.GetKeyState(win32con.VK_RBUTTON) < 0

                    if button_down and not prev_button:
                        cursor_pos = win32gui.GetCursorPos()

                        if self.is_click_in_dolphin(*cursor_pos):
                            window_x, window_y = self.screen_to_window(*cursor_pos)
                            percent_x, percent_y = self.window_to_percent(window_x, window_y)

                            self.control_window.after(0, lambda px=percent_x, py=percent_y: self.handle_click(px, py))

                            while win32api.GetKeyState(win32con.VK_RBUTTON) < 0:
                                time.sleep(0.01)

                    prev_button = button_down
                    time.sleep(0.01)

                except Exception:
                    time.sleep(0.1)

        thread = threading.Thread(target=detector, daemon=True)
        thread.start()

    def handle_click(self, percent_x, percent_y):
        print(f"\n🎯 Position: {percent_x:.2f}%, {percent_y:.2f}%")

        # Create property selection dialog
        self.show_property_selection_dialog(percent_x, percent_y)

    def show_property_selection_dialog(self, percent_x, percent_y):
        """Show dialog to select which property to mark at this location"""
        dialog = tk.Toplevel(self.control_window)
        dialog.title("Select Property")
        dialog.geometry("400x500+200+200")
        dialog.configure(bg='#2b2b2b')
        dialog.attributes('-topmost', True)
        dialog.transient(self.control_window)
        dialog.grab_set()

        # Title
        title_label = tk.Label(dialog, text="🏠 Select Property to Mark",
                               fg='#00ff00', bg='#2b2b2b', font=('Arial', 12, 'bold'))
        title_label.pack(pady=10)

        # Position info
        pos_label = tk.Label(dialog, text=f"Position: {percent_x:.2f}%, {percent_y:.2f}%",
                             fg='white', bg='#2b2b2b', font=('Arial', 10))
        pos_label.pack(pady=5)

        # Property list
        list_frame = tk.Frame(dialog, bg='#1e1e1e', relief='sunken', bd=1)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)

        prop_listbox = tk.Listbox(list_frame, bg='#1e1e1e', fg='white',
                                  font=('Consolas', 9), selectmode=tk.SINGLE)
        prop_scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=prop_listbox.yview)
        prop_listbox.configure(yscrollcommand=prop_scrollbar.set)

        prop_listbox.pack(side='left', fill='both', expand=True)
        prop_scrollbar.pack(side='right', fill='y')

        # Populate property list
        properties = self.monopoly_data.get('properties', [])
        property_items = []

        for prop in properties:
            has_coords = '✓' if 'coordinates' in prop else '✗'
            type_icon = {'property': '🏠', 'station': '🚂', 'utility': '⚡'}.get(prop.get('type', ''), '🏠')
            display_text = f"{has_coords} {type_icon} {prop['name']}"
            property_items.append((prop, display_text))
            prop_listbox.insert(tk.END, display_text)

        # Buttons
        btn_frame = tk.Frame(dialog, bg='#2b2b2b')
        btn_frame.pack(pady=10)

        def on_mark():
            selection = prop_listbox.curselection()
            if selection:
                selected_prop, _ = property_items[selection[0]]
                self.mark_property_at_position(selected_prop, percent_x, percent_y)
                dialog.destroy()
            else:
                messagebox.showwarning("No Selection", "Please select a property to mark")

        def on_cancel():
            dialog.destroy()

        tk.Button(btn_frame, text="Mark Property", bg='#66bb6a', fg='white',
                  font=('Arial', 10), command=on_mark).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cancel", bg='#ef5350', fg='white',
                  font=('Arial', 10), command=on_cancel).pack(side='left', padx=5)

        # Select first unmarked property by default
        for i, (prop, _) in enumerate(property_items):
            if 'coordinates' not in prop:
                prop_listbox.selection_set(i)
                prop_listbox.see(i)
                break

    def mark_property_at_position(self, selected_prop, percent_x, percent_y):
        """Mark the selected property at the given position"""
        # Get window info for pixel coordinates
        info = self.get_window_info()
        pixel_x = int((percent_x / 100) * info['width']) if info else 0
        pixel_y = int((percent_y / 100) * info['height']) if info else 0

        # Add/update coordinates
        selected_prop['coordinates'] = {
            'x_relative': round(percent_x / 100, 4),
            'y_relative': round(percent_y / 100, 4),
            'x_pixel': pixel_x,
            'y_pixel': pixel_y,
            'window_size': {
                'width': info['width'] if info else 0,
                'height': info['height'] if info else 0
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f"✅ Marked: '{selected_prop['name']}' at ({percent_x:.2f}%, {percent_y:.2f}%)")

        # Auto-save and update UI
        self.save_properties()
        self.update_property_list()

    def update_property_list(self):
        self.listbox.delete(0, tk.END)

        properties = self.monopoly_data.get('properties', [])
        for prop in properties:
            has_coords = '✓' if 'coordinates' in prop else '✗'
            type_icon = {'property': '🏠', 'station': '🚂', 'utility': '⚡'}.get(prop.get('type', ''), '🏠')

            if 'coordinates' in prop:
                coords = prop['coordinates']
                display_text = f"{has_coords} {type_icon} {prop['name']} ({coords['x_relative']:.3f}, {coords['y_relative']:.3f})"
            else:
                display_text = f"{has_coords} {type_icon} {prop['name']} (no coordinates)"

            self.listbox.insert(tk.END, display_text)

    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            properties = self.monopoly_data.get('properties', [])
            if index < len(properties):
                prop = properties[index]

                self.summary_text.config(state=tk.NORMAL)
                self.summary_text.delete(1.0, tk.END)

                self.summary_text.insert(tk.END, f"Name: {prop['name']}\n")
                self.summary_text.insert(tk.END, f"ID: {prop['id']}\n")
                self.summary_text.insert(tk.END, f"Type: {prop.get('type', 'unknown')}\n")
                self.summary_text.insert(tk.END, f"Value: £{prop.get('value', 0)}\n")

                if 'coordinates' in prop:
                    coords = prop['coordinates']
                    self.summary_text.insert(tk.END, f"\nCoordinates:\n")
                    self.summary_text.insert(tk.END,
                                             f"Relative: ({coords['x_relative']:.4f}, {coords['y_relative']:.4f})\n")
                    self.summary_text.insert(tk.END, f"Pixel: ({coords['x_pixel']}, {coords['y_pixel']})\n")
                    self.summary_text.insert(tk.END, f"Updated: {coords.get('timestamp', 'unknown')}")
                else:
                    self.summary_text.insert(tk.END, f"\nNo coordinates set")

                self.summary_text.config(state=tk.DISABLED)

    def delete_selected_coordinates(self):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            properties = self.monopoly_data.get('properties', [])
            if index < len(properties):
                prop = properties[index]

                if 'coordinates' not in prop:
                    messagebox.showinfo("Remove Coordinates",
                                        f"'{prop['name']}' has no coordinates to remove",
                                        parent=self.control_window)
                    return

                result = messagebox.askyesno("Remove Coordinates",
                                             f"Remove coordinates from '{prop['name']}'?",
                                             parent=self.control_window)
                if result:
                    del prop['coordinates']
                    print(f"🗑️  Removed coordinates from: {prop['name']}")
                    self.save_properties()
                    self.update_property_list()

                    # Clear summary
                    self.summary_text.config(state=tk.NORMAL)
                    self.summary_text.delete(1.0, tk.END)
                    self.summary_text.config(state=tk.DISABLED)
        else:
            messagebox.showinfo("Remove Coordinates", "No property selected",
                                parent=self.control_window)

    def clear_all_coordinates(self):
        properties = self.monopoly_data.get('properties', [])
        coords_count = sum(1 for p in properties if 'coordinates' in p)

        if coords_count == 0:
            messagebox.showinfo("Clear All", "No coordinates to clear",
                                parent=self.control_window)
            return

        result = messagebox.askyesno("Clear All Coordinates",
                                     f"Clear coordinates from all {coords_count} marked properties?",
                                     parent=self.control_window)
        if result:
            for prop in properties:
                if 'coordinates' in prop:
                    del prop['coordinates']

            print("🧹 All coordinates cleared")
            self.save_properties()
            self.update_property_list()

            # Clear summary
            self.summary_text.config(state=tk.NORMAL)
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.config(state=tk.DISABLED)

    def manual_save(self):
        self.save_properties()
        properties = self.monopoly_data.get('properties', [])
        coords_count = sum(1 for p in properties if 'coordinates' in p)
        messagebox.showinfo("Saved", f"Saved coordinates for {coords_count} properties to:\n{self.filename}",
                            parent=self.control_window)

    def quit(self):
        properties = self.monopoly_data.get('properties', [])
        coords_count = sum(1 for p in properties if 'coordinates' in p)

        if coords_count > 0:
            result = messagebox.askyesnocancel("Quit",
                                               f"Save coordinates for {coords_count} properties before quitting?",
                                               parent=self.control_window)
            if result is True:
                self.save_properties()
            elif result is None:
                return

        print(f"\n🛑 Stopping property manager...")
        self.tracking = False
        if self.overlay:
            self.overlay.destroy()
        if self.control_window:
            self.control_window.quit()

    def run(self):
        print("🏠 Persistent Monopoly Property Manager")
        print("=" * 50)

        # Load existing properties first
        if not self.load_monopoly_properties():
            return

        if not self.find_dolphin_window():
            return

        print("\n▶️  Starting persistent manager...")
        print(f"   📄 Using: {self.filename}")
        print("   📍 Right-click in Dolphin to mark/update properties")
        print("   🔄 All changes auto-saved")
        print("   🏠 Properties = lime, 🚂 Stations = cyan, ⚡ Utilities = yellow")
        print()

        self.tracking = True
        self.create_control_window()
        self.create_overlay()

        try:
            self.control_window.mainloop()
        except KeyboardInterrupt:
            print("\n❌ Interrupted by user")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            self.tracking = False
            print("\n✅ Property manager stopped")


if __name__ == "__main__":
    detector = PersistentPropertyDetector()
    detector.run()