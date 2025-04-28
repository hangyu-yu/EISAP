import dearpygui.dearpygui as dpg
import os
import glob
    
def select_files(config):
    """
    Update the selected file paths in the config.
    """
    if os.path.isdir(config.folder_path):
        config.file_list = sorted(glob.glob(os.path.join(config.folder_path, f"*{config.file_extensions}")))
        print("File list:", config.file_list)
        if not config.file_list:
            config.file_list = ['[Error] No file found! Recheck the folder path or file extension, otherwise report the issue.']
    else:
        config.file_list = ['[Error] Folder path not found! Recheck the folder path or report the issue.']

def update_selected_files(config, tag=None):
    """
    Update the list of selected files in config.selected_files.
    """
    config.selected_files = [os.path.basename(file) for file in config.file_list
                            if dpg.get_value(f"checkbox_{tag}_{os.path.basename(file)}")
                            ]
    for file in config.file_list:
        checkbox_tag = f"checkbox_{tag}_{os.path.basename(file)}"
        is_selected = os.path.basename(file) in config.selected_files
    dpg.set_value(checkbox_tag, is_selected)

def select_all_files(config, tag=None):
    """
    Select all files in the file list.
    """
    for file in config.file_list:
        checkbox_tag = f"checkbox_{tag}_{os.path.basename(file)}"
        dpg.set_value(checkbox_tag, True)
    update_selected_files(config, tag)

def unselect_all_files(config, tag=None):
    """
    Unselect all files in the file list.
    """
    for file in config.file_list:
        checkbox_tag = f"checkbox_{tag}_{os.path.basename(file)}"
        dpg.set_value(checkbox_tag, False)
    update_selected_files(config, tag)

def update_file_list(config, tag = None):
    """
    Update the file list based on the selected extension and default folder path.
    """
    config.file_extensions = dpg.get_value("file_extension_selector")
    select_files(config)
    dpg.delete_item(tag, children_only=True)

    with dpg.menu_bar(parent=tag):
        with dpg.menu(label="File list"):
            dpg.add_menu_item(label="Select all", callback=lambda: select_all_files(config, tag))
            dpg.add_menu_item(label="Unselect all", callback=lambda: unselect_all_files(config, tag))

    for file in config.file_list:
        filename = os.path.basename(file)
        checkbox_tag = f"checkbox_{tag}_{filename}"
        
        # Determine if this file should be checked
        should_check = any(
            os.path.basename(selected_file) == filename 
            for selected_file in config.selected_files
        )
        
        # Add checkbox with proper callback
        with dpg.group(parent=tag, horizontal=True):
            dpg.add_checkbox(
                label=filename,
                tag=checkbox_tag,
                default_value=should_check,
                callback=lambda s, a, f=filename: update_selected_files(config, tag)
            )