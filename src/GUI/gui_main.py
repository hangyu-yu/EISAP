import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import dearpygui.dearpygui as dpg
import src.GUI as gui
from src.GUI.config import Config
import platform
import ctypes

# 00 - Function Definitions
# Utility function to print the sender of the callback
def print_me(sender):
    print(f"Menu Item: {sender}")

def on_exit(config):
    config.save_config()
    print("[LOG] Configuration saved.")

# 01 - Initialization
# Set the DPI awareness to system DPI
if platform.system() == "Windows":
    import ctypes
    user32 = ctypes.windll.user32
    window_width = int(user32.GetSystemMetrics(0) * 0.8)
    window_height = int(user32.GetSystemMetrics(1) * 0.8)
elif platform.system() == "Darwin":  # macOS
    from tkinter import Tk
    root = Tk()
    root.withdraw()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)
else:
    raise OSError("Unsupported operating system")

# Initialize the configuration
config = Config()

# Initialize DearPyGui
dpg.create_context()
dpg.create_viewport(title='SOCEIS', width=window_width, height=window_height)

# Setup the icon
icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons", "app_icon.ico")
dpg.set_viewport_small_icon(icon_path)
dpg.set_viewport_large_icon(icon_path)

# Setup the fonts
with dpg.font_registry():
    default_font = dpg.add_font(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "fonts", "MiSans-Medium.otf"), 20)
    second_font = dpg.add_font(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "fonts", "MiSans-Light.otf"), 10)
dpg.bind_font(default_font)

# 02 - Set up different windows
with dpg.window(label="Main Window", tag='fullscreen'):
    with dpg.menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Save", callback=print_me)
            dpg.add_menu_item(label="Save As", callback=print_me)

        with dpg.menu(label="Settings"):
            dpg.add_menu_item(label="Setting 1", callback=print_me, check=True)
            dpg.add_menu_item(label="Setting 2", callback=print_me)

        dpg.add_menu_item(label="Help", callback=print_me)

    with dpg.tab_bar():
        gui.gui_tab_soceis(config)

# 05 - Show the window
dpg.setup_dearpygui()
dpg.set_primary_window("fullscreen", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.set_exit_callback(on_exit(config))
dpg.destroy_context()
