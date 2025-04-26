import os
import dearpygui.dearpygui as dpg
import glob
import numpy as np
import pandas as pd
import src.Functions as fn
from src.Methods.DRT.DRT import DRT
from src.Methods.CNLS.Circuit import Circuit

def update_selected_files(config):
    """
    Update the list of selected files in config.selected_files.
    """
    config.selected_files = [
    os.path.basename(file) for file in config.file_list
    if dpg.get_value(f"checkbox_eis_{os.path.basename(file)}")
    ]
    for file in config.file_list:
        checkbox_tag = f"checkbox_eis_{os.path.basename(file)}"
        is_selected = os.path.basename(file) in config.selected_files
    dpg.set_value(checkbox_tag, is_selected)

def update_file_list(config):
    """
    Update the file list based on the selected extension and default folder path.
    """
    dpg.delete_item("child_window_file_list_eis", children_only=True)
    for file in config.file_list:
        filename = os.path.basename(file)
        checkbox_tag = f"checkbox_eis_{filename}"
        
        # Determine if this file should be checked
        should_check = any(
            os.path.basename(selected_file) == filename 
            for selected_file in config.selected_files
        )
        
        # Add checkbox with proper callback
        with dpg.group(parent="child_window_file_list_eis", horizontal=True):
            dpg.add_checkbox(
                label=filename,
                tag=checkbox_tag,
                default_value=should_check,
                callback=lambda s, a, f=filename: update_selected_files(config)
            )

def gui_tab_eis(config):
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    with dpg.tab(label="EIS", tag="tab_eis"):
        with dpg.group(horizontal=False, horizontal_spacing=0):
            with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.33), horizontal_scrollbar=True, menubar=False, tag="child_window_file_list_eis"):
                # with dpg.menu_bar():
                #     with dpg.menu(label="File list"):
                #         dpg.add_menu_item(label="")
                update_file_list(config)