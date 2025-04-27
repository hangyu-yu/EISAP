import os
import dearpygui.dearpygui as dpg
import glob
import numpy as np
import pandas as pd
import src.Functions as fn
import src.GUI.Utils as gui_utils
from src.Methods.DRT.DRT import DRT
from src.Methods.CNLS.Circuit import Circuit

def gui_tab_eis(config):
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    with dpg.tab(label="EIS", tag="tab_eis"):
        with dpg.group(horizontal=False, horizontal_spacing=0):
            with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.33), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_eis"):
                gui_utils.file_list.update_file_list(config, "child_window_file_list_eis")
                gui_utils.file_monitor.bind_tab_switch_update(
                    tab_tag="tab_eis",
                    config=config,
                    update_callback=lambda: gui_utils.file_list.update_file_list(
                        config, "child_window_file_list_eis"
                    )
                )