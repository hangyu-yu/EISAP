import os
import glob
import copy
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
from src.Methods.CNLS.Circuit import Circuit

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
    if dpg.does_item_exist(checkbox_tag):
        dpg.set_value(checkbox_tag, is_selected)
        
    config.display_file = config.selected_files[0] if config.selected_files else None
    if dpg.does_item_exist("combo_eis_plot_file"):
        dpg.configure_item("combo_eis_plot_file", items = config.selected_files, default_value = config.display_file)
    if dpg.does_item_exist("combo_drt_plot_file"):
        dpg.configure_item("combo_drt_plot_file", items = config.selected_files, default_value = config.display_file)
    print("Selected files:", config.selected_files)
    
    # Update the display file in the GUI
    if dpg.does_item_exist("group_eis_display_file"):
        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_eis_plot_file", "group_eis_display_file")
    if dpg.does_item_exist("group_drt_display_file"):
        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_drt_plot_file", "group_drt_display_file")
    if dpg.does_item_exist("group_cnls_display_file"):
        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_display_file_cnls", "group_cnls_display_file")

    # Update the plots-All in the GUI
    try:
        if dpg.does_item_exist("tab_bar_eis_plot_all"):
            gui_utils.eis_plots.update_all_plots(config)
        if dpg.does_item_exist("tab_bar_drt_plot_all"):
            gui_utils.drt_plots.update_all_plots(config)
        if dpg.does_item_exist("tab_bar_cnls_plot_all"):
            gui_utils.cnls_plots.update_all_plots(config)
    except:
        print("[Warning] EIS/DRT/CNLS ALL-plots update failed. Please check the EIS/DRT/CNLS data, or come to file_list.update_seleted_files and check.")

def select_all_files(config, tag=None):
    """
    Select all files in the file list.
    """
    for file in config.file_list:
        checkbox_tag = f"checkbox_{tag}_{os.path.basename(file)}"
        if dpg.does_item_exist(checkbox_tag):
            dpg.set_value(checkbox_tag, True)
    update_selected_files(config, tag)

def unselect_all_files(config, tag=None):
    """
    Unselect all files in the file list.
    """
    for file in config.file_list:
        checkbox_tag = f"checkbox_{tag}_{os.path.basename(file)}"
        if dpg.does_item_exist(checkbox_tag):
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
            for idx, file in enumerate(config.file_list):
                file_name_no_ext = os.path.splitext(os.path.basename(file))[0]
                if os.path.isdir(os.path.join(config.folder_path, "EIS")) and "[Error]" not in file:
                    if file_name_no_ext not in config.store.keys() or "EIS" not in config.store[file_name_no_ext].keys() or config.store[file_name_no_ext]['EIS'].raw['Re'] is None:
                        config.store[file_name_no_ext] = {}
                        config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_EIS()
                    
                        if idx == len(config.file_list) - 1:
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_EIS()
                            print(f"---- EIS data imported from {file} successfully.")
                
                if os.path.isdir(os.path.join(config.folder_path, "DRT")) and "[Error]" not in file:
                    if file_name_no_ext not in config.store.keys() or "EIS" not in config.store[file_name_no_ext].keys():
                        config.store[file_name_no_ext] = {}
                        config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_DRT()

                        if idx == len(config.file_list) - 1:
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_DRT()
                            print(f"---- DRT data imported from {file} successfully.")
                    elif config.store['beacon_DRT_import']:
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_DRT()

                        if idx == len(config.file_list) - 1:
                            EIS.file_folder = config.folder_path
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_DRT()
                            print(f"---- DRT data imported from {file} successfully.")

                if os.path.isdir(os.path.join(config.folder_path, "CNLS")) and "[Error]" not in file:
                    file_data = config.store.get(file_name_no_ext, {})
                    if "CNLS" not in file_data:
                        if file_name_no_ext not in config.store.keys():
                            config.store[file_name_no_ext] = {}
                        config.store[file_name_no_ext]['CNLS'] = Circuit(file_folder=config.folder_path, filename=os.path.basename(file), Elements = None, EIS = config.store[file_name_no_ext]['EIS'] if 'EIS' in config.store[file_name_no_ext].keys() and config.store[file_name_no_ext]['EIS'].tknv_truncated is not None else None, data_type = 'truncated')
                        CNLS_tmp = config.store[file_name_no_ext]['CNLS']
                        CNLS_tmp.ImportCircuit()
                    
                        if idx == len(config.file_list) - 1:
                            CNLS.file_folder = config.folder_path
                            CNLS.filename = os.path.basename(file)
                            CNLS.ImportCircuit()
                            config.store["Elements"] = CNLS.Elements if CNLS.Elements is not None else {}
                            config.store["segment_constraints"] = CNLS.constraint_type
                            print(f"---- CNLS data imported from {file} successfully.")
                            
            config.store['beacon_DRT_import'] = False

def display_file(sender, app_data, config):
    """
    Callback function to display the selected file in the combo box.
    """
    # Update the displayed file name in the GUI
    config.display_file = dpg.get_value(sender)

    # Update optimal lambda value in the DRT tab
    try:
        if dpg.does_item_exist("text_optimal_lambda") and config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt:
            dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.4e}")
    except:
        if dpg.does_item_exist("text_optimal_lambda"):
            dpg.set_value("text_optimal_lambda", "Non-calculated")
    
    # Update the EIS table and plots
    try:
        if dpg.does_item_exist("tab_eis"):
            gui_utils.eis_table.table_update(config)
            gui_utils.eis_plots.update_single_plots(config)
    except:
        print("------ EIS plots update failed. Please check the EIS data.")
        pass
    
    # Udpate the DRT table and plots
    try:
        if dpg.does_item_exist("tab_drt"):
            gui_utils.drt_table.table_update(config)
            gui_utils.drt_plots.update_single_plots(config)
    except:
        print("------ DRT plots update failed. Please check the DRT data.")
        pass

    # Update the CNLS table and plots
    try:    
        if dpg.does_item_exist("tab_cnls"):
            gui_utils.cnls_table.table_update(config)
            gui_utils.cnls_elements.update_elements(config)
            dpg.configure_item("combo_cnls_data_type", default_value = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].data_type)
            dpg.configure_item("combo_peak_ID", default_value = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_mode)
            dpg.configure_item("input_nbr_iters", default_value = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].iteration)
            dpg.configure_item("input_nbr_peaks", default_value = len(config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_fixed))
            gui_utils.cnls_functions.dynamic_peak_ids(0, 0, config)
            gui_utils.cnls_table.table_update(config)
            gui_utils.cnls_plots.update_single_plots(config)
    except:
        print("------ CNLS plots update failed. Please check the CNLS data.")
    # Print the selected file for debugging
    print(f"---- File to plot: {config.display_file}")

def update_file_list_and_display(sender, app_data, config, tag_name, parent_tag):
    if config.display_file is None or config.display_file == "":
        config.display_file = config.selected_files[0] if config.selected_files else None
    dpg.delete_item(tag_name)
    dpg.add_combo(
        parent=parent_tag,
        tag=tag_name,
        default_value = config.display_file,
        width = -1,
        items = config.selected_files,
        callback=lambda s, a: gui_utils.file_list.display_file(s, a, config)
    )