import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import shutil
import ctypes
import platform
import src.GUI as gui
import src.GUI.gui_tab_soceis as gui_tab_soceis_module
import src.GUI.gui_tab_eis as gui_tab_eis_module
import src.GUI.gui_tab_drt as gui_tab_drt_module
import src.GUI.gui_tab_cnls as gui_tab_cnls_module
from pathlib import Path
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg
from src.GUI.config import Config
from src.Methods.DRT.DRT import DRT
from src.Methods.CNLS.Circuit import Circuit


def _normalize_path(path_obj):
    """Handle Windows long path (260+ chars) by adding \\?\ prefix."""
    path_str = str(path_obj)
    if sys.platform == 'win32' and os.path.isabs(path_str) and not path_str.startswith('\\\\'):
        return '\\\\?' + os.path.sep + os.path.abspath(path_str)
    return path_str


# Importing submodules sets package attributes to module objects.
# Restore callable GUI entry points expected by the rest of the codebase.
gui.gui_tab_soceis = gui_tab_soceis_module.gui_tab_soceis
gui.gui_tab_eis = gui_tab_eis_module.gui_tab_eis
gui.gui_tab_drt = gui_tab_drt_module.gui_tab_drt
gui.gui_tab_cnls = gui_tab_cnls_module.gui_tab_cnls

# 00 - Function Definitions
# Utility function to print the sender of the callback
def on_exit(config):
    config.save_config()
    print("[LOG] SOCEIS is shutting down, cleaning up subprocesses...")
    if 'viewer_processes' in config.store:
        for proc in config.store['viewer_processes']:
            if proc.poll() is None:  # 如果进程还在运行
                proc.terminate()      # 尝试优雅关闭
                # proc.kill()        # 如果想强制关闭可以用这个
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

base_viewport_width = window_width
base_viewport_height = window_height

# Setup the icon and fonts
root_dir = Path(__file__).resolve().parent.parent.parent
# Function to check if path contains special characters
def has_special_chars(path_str):
    try:
        path_str.encode('ascii')
        return False
    except UnicodeEncodeError:
        return True
# Font handling with temporary directory only if needed
try:
    font_path_medium = root_dir / "assets" / "fonts" / "MiSans-Medium.otf"
    font_path_light = root_dir / "assets" / "fonts" / "MiSans-Light.otf"

    icons_dir = root_dir / "assets" / "icons"
    icon_ico = icons_dir / "app_icon.ico"
    icon_png = icons_dir / "app_icon.png"

    system_name = platform.system()
    icon_path = None

    if system_name == "Windows":
        # Windows prefers .ico and can fail on some non-ASCII paths.
        if has_special_chars(str(root_dir)):
            temp_dir = Path("C:/Temp/SOCEIS_Assets")
            temp_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root_dir / "assets" / "fonts" / "MiSans-Medium.otf", _normalize_path(temp_dir / "MiSans-Medium.otf"))
            shutil.copy2(root_dir / "assets" / "fonts" / "MiSans-Light.otf", _normalize_path(temp_dir / "MiSans-Light.otf"))
            font_path_medium = temp_dir / "MiSans-Medium.otf"
            font_path_light = temp_dir / "MiSans-Light.otf"

            # Always refresh icon file in temp to avoid stale/cached wrong icon.
            if icon_ico.exists():
                shutil.copy2(icon_ico, _normalize_path(temp_dir / "app_icon.ico"))
                icon_path = temp_dir / "app_icon.ico"
            elif icon_png.exists():
                shutil.copy2(icon_png, _normalize_path(temp_dir / "app_icon.png"))
                icon_path = temp_dir / "app_icon.png"
        else:
            icon_path = icon_ico if icon_ico.exists() else (icon_png if icon_png.exists() else None)
    elif system_name == "Linux":
        # Linux commonly works better with PNG icon.
        icon_path = icon_png if icon_png.exists() else (icon_ico if icon_ico.exists() else None)
    else:  # Darwin/macOS
        # macOS may ignore runtime viewport icon depending on backend/window manager.
        icon_path = icon_png if icon_png.exists() else (icon_ico if icon_ico.exists() else None)

    # Set viewport icons (best effort).
    if icon_path is not None:
        try:
            dpg.set_viewport_small_icon(str(icon_path))
            dpg.set_viewport_large_icon(str(icon_path))
        except Exception as icon_err:
            print(f"[WARNING] Failed to set viewport icon from {icon_path}: {icon_err}")
    else:
        print("[WARNING] No app icon file found (expected app_icon.ico or app_icon.png).")

    # Load fonts
    with dpg.font_registry():
        default_font = dpg.add_font(str(font_path_medium), int(config.font_size))
        second_font = dpg.add_font(str(font_path_light), int(config.font_size)/2)
        dpg.bind_font(default_font)
except Exception as e:
    print(f"[WARNING] Asset loading failed: {e}")
    # Fallback to system font
    with dpg.font_registry():
        default_font = dpg.add_font("arial.ttf", int(config.font_size))
        dpg.bind_font(default_font)

with dpg.theme() as plot_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 3, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, value=[0,0,0,0], category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerWeight, 2, category=dpg.mvThemeCat_Plots)

# 02 - Set up different windows
with dpg.window(label="Main Window", tag='fullscreen'):
    with dpg.menu_bar():
        # with dpg.menu(label="File"):
        #     dpg.add_menu_item(label="Save", callback=print_me)
        #     dpg.add_menu_item(label="Save As", callback=print_me)

        with dpg.menu(label="Settings"):
            # dpg.add_menu_item(label="Setting 1", callback=print_me, check=True)
            dpg.add_menu_item(label="Font size", callback=lambda sender, app_data: gui_utils.small_functions.font_size_callback(sender, app_data, config, font_path_medium, font_path_light))
            dpg.add_menu_item(label="Update from GitHub", callback=lambda sender, app_data: gui_utils.small_functions.start_online_update_callback(sender, app_data, config))

        # dpg.add_menu_item(label="Help", callback=print_me)
        dpg.bind_theme(plot_theme)

    with dpg.tab_bar(tag="tab_bar_main", reorderable=True):
        gui.gui_tab_soceis(config, EIS, CNLS)

def global_viewport_resize_callback(sender=None, app_data=None):
    """
    Single resize callback for the whole app.
    Avoids callback overrides between tabs and keeps font/layout scaling consistent.
    """
    viewport_width = max(1, dpg.get_viewport_width())
    viewport_height = max(1, dpg.get_viewport_height())

    # Adaptive global font scale around the configured base size.
    scale_w = viewport_width / max(1, base_viewport_width)
    scale_h = viewport_height / max(1, base_viewport_height)
    font_scale = min(scale_w, scale_h)
    dpg.set_global_font_scale(max(0.85, min(1.35, font_scale)))

    # Update each tab layout function safely.
    try:
        gui_tab_soceis_module.update_image_sizes()
    except Exception:
        pass
    try:
        gui_tab_eis_module.update_child_window_size()
    except Exception:
        pass
    try:
        gui_tab_drt_module.update_child_window_size()
    except Exception:
        pass
    try:
        gui_tab_cnls_module.update_child_window_size()
    except Exception:
        pass

# 05 - Show the window
dpg.setup_dearpygui()
dpg.set_viewport_resize_callback(global_viewport_resize_callback)
global_viewport_resize_callback()
dpg.set_primary_window("fullscreen", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.set_exit_callback(on_exit(config))
dpg.destroy_context()
