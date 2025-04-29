import os
import glob
import copy
import dearpygui.dearpygui as dpg

def select_files(config, tag):
    """
    Update the selected file paths in the config.
    """
    if os.path.isdir(config.folder_path):
        config.file_list = sorted(glob.glob(os.path.join(config.folder_path, f"*{config.file_extensions}")))
        print(f"---- File list from [{tag}]:", config.file_list)
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
    print("Selected files:", config.selected_files)

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

def update_file_list(config, tag = None, EIS = None, CNLS = None):
    """
    Update the file list based on the selected extension and default folder path.
    """
    config.file_extensions = dpg.get_value("file_extension_selector")
    select_files(config, tag)
    dpg.delete_item(tag, children_only=True)

    with dpg.menu_bar(parent=tag):
        with dpg.menu(label="File list"):
            dpg.add_menu_item(label="Select all", callback=lambda: select_all_files(config, tag))
            dpg.add_menu_item(label="Unselect all", callback=lambda: unselect_all_files(config, tag))
            dpg.add_menu_item(label="Refresh", callback=lambda: update_file_list(config, tag))

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
        
        # Import all the data if there is historical data
        if (os.path.isdir(os.path.join(config.folder_path, "EIS")) and os.path.isdir(os.path.join(config.folder_path, "DRT"))) or os.path.isdir(os.path.join(config.folder_path, "CNLS")):
            for idx, file in enumerate(config.file_list):
                file_name_no_ext = os.path.splitext(os.path.basename(file))[0]
                if file_name_no_ext not in config.store.keys() and "[Error]" not in file:
                    config.store[file_name_no_ext] = {}
                    config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                    EIS_tmp = config.store[file_name_no_ext]['EIS']
                    EIS_tmp.filename = os.path.basename(file)
                    EIS_tmp.import_data()

                    config.store[file_name_no_ext]['CNLS'] = copy.deepcopy(CNLS)
                    CNLS_tmp = config.store[file_name_no_ext]['CNLS']
                    CNLS_tmp.file_folder = config.folder_path
                    CNLS_tmp.filename = os.path.basename(file)
                    CNLS_tmp.ImportCircuit()
                    if idx == len(config.file_list) - 1:
                        EIS.filename = os.path.basename(file)
                        EIS.import_data()
                        CNLS.file_folder = config.folder_path
                        CNLS.filename = os.path.basename(file)
                        CNLS.ImportCircuit()

                        print(f"---- Data imported from {file} successfully.")
            breakpoint
