import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import ctypes
import platform
import src.GUI as gui
from pathlib import Path
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg
from src.GUI.config import Config
from src.Methods.DRT.DRT import DRT
from src.Methods.CNLS.Circuit import Circuit

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
config.store['beacon_DRT_import'] = True
EIS = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=12.56, n_cell=1, file_folder=config.folder_path, filename=None)
CNLS = Circuit(file_folder=config.folder_path, filename=None, Elements = None, EIS = None, data_type = None)

# Initialize DearPyGui
dpg.create_context()
dpg.create_viewport(title='SOCEIS', width=window_width, height=window_height)

# Setup the icon and fonts
root_dir = Path(__file__).resolve().parent.parent.parent
icon_path = root_dir / "assets" / "icons" / "app_icon.ico"
font_path_medium = root_dir / "assets" / "fonts" / "MiSans-Medium.otf"
font_path_light = root_dir / "assets" / "fonts" / "MiSans-Light.otf"
dpg.set_viewport_small_icon(str(icon_path))
dpg.set_viewport_large_icon(str(icon_path))
with dpg.font_registry():
    default_font = dpg.add_font(str(font_path_medium), 20)
    second_font = dpg.add_font(str(font_path_light), 10)
dpg.bind_font(default_font)

with dpg.theme() as plot_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, value=[0,0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerWeight, 2, category=dpg.mvThemeCat_Plots)

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
        dpg.bind_theme(plot_theme)

    with dpg.tab_bar(tag="tab_bar_main", reorderable=True):
        gui.gui_tab_soceis(config, EIS, CNLS)

# 05 - Show the window
dpg.setup_dearpygui()
dpg.set_primary_window("fullscreen", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.set_exit_callback(on_exit(config))
dpg.destroy_context()
