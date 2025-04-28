# src/GUI/Utils/file_monitor.py
import dearpygui.dearpygui as dpg
from typing import Callable

def bind_tab_switch_update(tab_tag: str, config, update_callback: Callable):
    """Bind file list update when switching tabs
    Args:
        tab_tag: The tag of the tab to monitor (e.g., "tab_eis")
        config: Global configuration object (must include file_list)
        update_callback: Callback function to execute on tab switch
    """
    # Initialize a copy of the configuration
    if not hasattr(config, "_file_list_previous"):
        config._file_list_previous = config.file_list.copy()

    # Use visible_handler to trigger when the tab becomes visible
    with dpg.item_handler_registry(tag=f"handler_{tab_tag}"):
        dpg.add_item_visible_handler(callback=lambda: _on_tab_switch(config, update_callback))
    dpg.bind_item_handler_registry(tab_tag, f"handler_{tab_tag}")

def _on_tab_switch(config, update_callback: Callable):
    """Actual switching logic: Compare file list differences and execute callback"""
    if config.file_list != config._file_list_previous:
        config._file_list_previous = config.file_list.copy()
        update_callback()