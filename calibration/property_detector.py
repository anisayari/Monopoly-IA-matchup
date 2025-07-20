import tkinter as tk
from tkinter import ttk
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


class PropertyDetector:
    def __init__(self):
        self.dolphin_hwnd = None
        self.overlay = None
        self.control_window = None
        self.canvas = None
        self.summary_text = None
        self.properties = []
        self.tracking = False
        self.monopoly_properties = self.load_monopoly_properties()
        self.current_property_index = 0
        self.property_coordinates = {}

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
        return int(percent_x * info['width']), int(percent_y * info['height'])

    def is_click_in_dolphin(self, screen_x, screen_y):
        info = self.get_window_info()
        if not info:
            return False

        return (info['left'] <= screen_x <= info['left'] + info['width'] and
                info['top'] <= screen_y <= info['top'] + info['height'])

    def create_control_window(self):
        self.control_window = tk.Tk()
        self.control_window.title("Property Detector")
        self.control_window.geometry("250x300+50+50")
        self.control_window.configure(bg='#2b2b2b')
        self.control_window.attributes('-topmost', True)

        main_frame = tk.Frame(self.control_window, bg='#2b2b2b', padx=10, pady=10)
        main_frame.pack(fill='both', expand=True)

        # Title
        title_label = tk.Label(main_frame, text="🎯 Property Detector",
                               fg='#00ff00', bg='#2b2b2b', font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        # Instructions
        self.inst_label = tk.Label(main_frame, text="Right-click in Dolphin to mark",
                              fg='white', bg='#2b2b2b', font=('Arial', 9))
        self.inst_label.pack(pady=(0, 15))
        
        # Progress label
        self.progress_label = tk.Label(main_frame, text="",
                              fg='yellow', bg='#2b2b2b', font=('Arial', 10, 'bold'))
        self.progress_label.pack(pady=(0, 10))

        # Buttons frame
        btn_frame = tk.Frame(main_frame, bg='#2b2b2b')
        btn_frame.pack(fill='x', pady=(0, 15))

        # Create buttons
        btn_style = {'font': ('Arial', 10), 'width': 8, 'height': 1}

        tk.Button(btn_frame, text="Undo", bg='#ff6b6b', fg='white',
                  command=self.undo_last, **btn_style).grid(row=0, column=0, padx=2, pady=2)

        tk.Button(btn_frame, text="Skip", bg='#ffa726', fg='white',
                  command=self.skip_property, **btn_style).grid(row=0, column=1, padx=2, pady=2)

        tk.Button(btn_frame, text="Save", bg='#66bb6a', fg='white',
                  command=self.save_properties, **btn_style).grid(row=1, column=0, padx=2, pady=2)

        tk.Button(btn_frame, text="Quit", bg='#ef5350', fg='white',
                  command=self.quit, **btn_style).grid(row=1, column=1, padx=2, pady=2)

        # Summary section
        summary_label = tk.Label(main_frame, text="📊 Properties:",
                                 fg='#00ff00', bg='#2b2b2b', font=('Arial', 10, 'bold'))
        summary_label.pack(anchor='w', pady=(0, 5))

        # Summary text area
        summary_frame = tk.Frame(main_frame, bg='#1e1e1e', relief='sunken', bd=1)
        summary_frame.pack(fill='both', expand=True)

        self.summary_text = tk.Text(summary_frame, bg='#1e1e1e', fg='white',
                                    font=('Consolas', 8), wrap=tk.WORD,
                                    height=8, state=tk.DISABLED)

        scrollbar = tk.Scrollbar(summary_frame, orient='vertical', command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=scrollbar.set)

        self.summary_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.update_summary()
    
    def load_monopoly_properties(self):
        """Charge le fichier MonopolyProperties.json"""
        try:
            properties_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "game_files", "MonopolyProperties.json")
            if os.path.exists(properties_file):
                with open(properties_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filtrer seulement les propriétés (pas les cases spéciales)
                    properties = [p for p in data['properties'] if p.get('type') in ['property', 'station', 'utility']]
                    print(f"✅ Loaded {len(properties)} properties from MonopolyProperties.json")
                    return properties
            else:
                print(f"❌ MonopolyProperties.json not found at {properties_file}")
                return []
        except Exception as e:
            print(f"❌ Error loading properties: {e}")
            return []

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

        # Afficher les propriétés déjà marquées
        for prop_id, coords in self.property_coordinates.items():
            prop = next((p for p in self.monopoly_properties if p['id'] == prop_id), None)
            if prop:
                x, y = self.percent_to_window(coords['x_relative'], coords['y_relative'])

                # Cercle vert pour les propriétés marquées
                circle = self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8,
                                                 fill='lime', outline='white', width=2)

                # Nom de la propriété
                name_bg = self.canvas.create_rectangle(x + 12, y - 8, x + 12 + len(prop['name']) * 7, y + 8,
                                                       fill='yellow', outline='black')

                name_text = self.canvas.create_text(x + 15, y, text=prop['name'],
                                                    fill='black', font=('Arial', 9), anchor='w')

    def update_summary(self):
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)

        # Mettre à jour l'instruction pour la propriété actuelle
        if self.current_property_index < len(self.monopoly_properties):
            current_prop = self.monopoly_properties[self.current_property_index]
            self.inst_label.config(text=f"Click on: {current_prop['name']}")
            self.progress_label.config(text=f"Progress: {len(self.property_coordinates)}/{len(self.monopoly_properties)}")
        else:
            self.inst_label.config(text="All properties marked!")
            self.progress_label.config(text=f"Completed: {len(self.property_coordinates)}/{len(self.monopoly_properties)}")

        # Afficher les propriétés déjà marquées
        if not self.property_coordinates:
            self.summary_text.insert(tk.END, "No properties marked yet.\n\n")
        else:
            self.summary_text.insert(tk.END, f"Marked: {len(self.property_coordinates)} properties\n\n")
            for prop_id, coords in self.property_coordinates.items():
                prop = next((p for p in self.monopoly_properties if p['id'] == prop_id), None)
                if prop:
                    self.summary_text.insert(tk.END, f"✓ {prop['name']}\n")
                    self.summary_text.insert(tk.END, f"  Rel: ({coords['x_relative']:.3f}, {coords['y_relative']:.3f})\n")
                    self.summary_text.insert(tk.END, f"  Abs: ({coords['x_pixel']}, {coords['y_pixel']})\n\n")

        self.summary_text.config(state=tk.DISABLED)

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
        if self.current_property_index >= len(self.monopoly_properties):
            print("✅ All properties already marked!")
            return
            
        current_prop = self.monopoly_properties[self.current_property_index]
        print(f"\n🎯 Marking: {current_prop['name']}")
        print(f"   Position: {percent_x:.2f}%, {percent_y:.2f}%")

        # Get window info for pixel coordinates
        info = self.get_window_info()
        pixel_x = int((percent_x / 100) * info['width']) if info else 0
        pixel_y = int((percent_y / 100) * info['height']) if info else 0

        # Sauvegarder les coordonnées pour cette propriété
        self.property_coordinates[current_prop['id']] = {
            'x_relative': round(percent_x / 100, 4),
            'y_relative': round(percent_y / 100, 4),
            'x_pixel': pixel_x,
            'y_pixel': pixel_y
        }
        
        print(f"✅ Marked: '{current_prop['name']}' ({len(self.property_coordinates)}/{len(self.monopoly_properties)})")
        
        # Passer à la propriété suivante
        self.current_property_index += 1
        self.update_summary()

    def undo_last(self):
        if self.property_coordinates and self.current_property_index > 0:
            # Trouver la dernière propriété marquée
            self.current_property_index -= 1
            prop_to_remove = self.monopoly_properties[self.current_property_index]
            
            if prop_to_remove['id'] in self.property_coordinates:
                del self.property_coordinates[prop_to_remove['id']]
                print(f"↶ Removed: {prop_to_remove['name']}")
                self.update_summary()
        else:
            print("❌ No properties to remove")

    def skip_property(self):
        """Passer à la propriété suivante sans la marquer"""
        if self.current_property_index < len(self.monopoly_properties):
            skipped_prop = self.monopoly_properties[self.current_property_index]
            print(f"⏭  Skipped: {skipped_prop['name']}")
            self.current_property_index += 1
            self.update_summary()
        else:
            print("✅ All properties already processed!")

    def save_properties(self):
        if not self.property_coordinates:
            tk.messagebox.showwarning("Save", "No properties marked to save",
                                      parent=self.control_window)
            return

        # Charger le fichier MonopolyProperties.json existant
        properties_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "game_files", "MonopolyProperties.json")
        
        try:
            # Charger les données existantes
            with open(properties_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Obtenir les infos de la fenêtre
            info = self.get_window_info()
            
            # Ajouter les coordonnées à chaque propriété
            for prop in data['properties']:
                if prop['id'] in self.property_coordinates:
                    coords = self.property_coordinates[prop['id']]
                    prop['coordinates'] = {
                        'x_relative': coords['x_relative'],
                        'y_relative': coords['y_relative'],
                        'x_pixel': coords['x_pixel'],
                        'y_pixel': coords['y_pixel'],
                        'window_size': {
                            'width': info['width'] if info else 0,
                            'height': info['height'] if info else 0
                        },
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            
            # Sauvegarder le fichier mis à jour
            with open(properties_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Updated {len(self.property_coordinates)} properties in {properties_file}")
            tk.messagebox.showinfo("Saved", f"Updated {len(self.property_coordinates)} properties in:\nMonopolyProperties.json",
                                   parent=self.control_window)
        except Exception as e:
            print(f"❌ Save error: {e}")
            tk.messagebox.showerror("Error", f"Save failed:\n{e}",
                                    parent=self.control_window)

    def quit(self):
        if self.property_coordinates:
            result = tk.messagebox.askyesnocancel("Quit",
                                                  f"Save {len(self.property_coordinates)} marked properties before quitting?",
                                                  parent=self.control_window)
            if result is True:
                self.save_properties()
            elif result is None:
                return

        print(f"\n🛑 Stopping detector...")
        self.tracking = False
        if self.overlay:
            self.overlay.destroy()
        if self.control_window:
            self.control_window.quit()

    def run(self):
        print("🎮 Dolphin Property Detector")
        print("=" * 40)

        if not self.find_dolphin_window():
            return

        print("\n▶️  Starting detection...")
        print(f"   📋 {len(self.monopoly_properties)} properties to mark")
        print("   📍 Right-click in Dolphin to mark properties")
        print("   🎛️  Use control window for management")
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
            print("\n✅ Detection complete")


if __name__ == "__main__":
    import tkinter.messagebox

    detector = PropertyDetector()
    detector.run()