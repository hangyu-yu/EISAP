import sys
import os
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
import ctypes

# 01 - Initialization
# Set the DPI awareness to system DPI
user32 = ctypes.windll.user32
window_width  = int(user32.GetSystemMetrics(0) * 0.8)
window_height = int(user32.GetSystemMetrics(1) * 0.8)

# Initialize DearPyGui
dpg.create_context()

# 02 - Set up different windows
with dpg.window(label = "Example Window"):
    dpg.add_text("Hello, World!")
    dpg.add_button(label="Click Me", callback=lambda: print("Button clicked!"))
    dpg.add_input_text(label="Input Text", default_value="Type here...")
    dpg.add_slider_float(label="Slider", default_value=0.5, min_value=0.0, max_value=1.0)

with dpg.window(label="Tutorial"):

    # configuration set when button is created
    dpg.add_button(label="Apply", width=300)

    # user data and callback set any time after button has been created
    btn = dpg.add_button(label="Apply 2")
    dpg.set_item_label(btn, "Button 57")
    dpg.set_item_width(btn, 200)

dpg.show_item_registry()

dpg.create_viewport(title='SOCEIS', width=window_width, height=window_height)

# 05 - Show the window
# Setup the icon
icon_path = os.path.join(os.path.dirname(sys.path[0]), "assets", "icons", "app_icon.ico")
dpg.set_viewport_small_icon(icon_path)
dpg.set_viewport_large_icon(icon_path)

# Setup the fonts
with dpg.font_registry():
    default_font = dpg.add_font(os.path.join(os.path.dirname(sys.path[0]), "assets", "fonts", "MiSans-Medium.otf"), 20)
    second_font = dpg.add_font(os.path.join(os.path.dirname(sys.path[0]), "assets", "fonts", "MiSans-Light.otf"), 10)
dpg.bind_font(default_font)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()