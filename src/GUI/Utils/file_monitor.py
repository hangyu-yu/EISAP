# src/GUI/Utils/file_monitor.py
import dearpygui.dearpygui as dpg
from typing import Callable
import os

def bind_tab_switch_update(tab_tag: str, config, update_callback: Callable):
    """Bind file list update when switching tabs using visibility handler.
    Args:
        tab_tag: The tag of the tab to monitor (e.g., "tab_eis")
        config: Global configuration object (must include file_list and folder_path)
        update_callback: Callback function to execute on tab switch
    """
    # Initialize previous file list state
    if not hasattr(config, "_file_list_previous"):
        config._file_list_previous = _get_normalized_file_list(config)

    # Create handler registry for visibility events
    handler_tag = f"visible_handler_{tab_tag}"
    if dpg.does_item_exist(handler_tag):
        dpg.delete_item(handler_tag)  # Avoid duplicate handlers

    with dpg.item_handler_registry(tag=handler_tag):
        dpg.add_item_visible_handler(
            callback=lambda: _on_tab_visible(tab_tag, config, update_callback)  # Pass tab_tag to print
        )
    
    dpg.bind_item_handler_registry(tab_tag, handler_tag)
    print(f"[Tab Monitor] 已绑定 Tab 切换监听: {tab_tag}")  # 初始化完成提示

def _get_normalized_file_list(config):
    """Normalize file list for comparison (handle path separators and case sensitivity)"""
    return [os.path.normcase(os.path.normpath(f)) for f in config.file_list]

def _on_tab_visible(tab_tag: str, config, update_callback: Callable):
    """Trigger callback when tab becomes visible and file list changes"""
    print(f"[Tab Monitor] 检测到 Tab 切换: {tab_tag}")  # Tab 切换事件打印
    
    current_files = _get_normalized_file_list(config)
    previous_files = getattr(config, "_file_list_previous", [])

    if current_files != previous_files:
        print(f"[Tab Monitor] 文件列表变化 detected in {tab_tag}")  # 文件变化打印
        config._file_list_previous = current_files.copy()
        update_callback()
    else:
        print(f"[Tab Monitor] 文件列表未变化 (Tab: {tab_tag})")  # 无变化时打印
