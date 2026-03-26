import os
import re
import glob
import copy
import numpy as np
from natsort import natsorted
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
from src.Methods.CNLS.Circuit import Circuit


def _normalize_path(path_obj):
    """Handle Windows long path (260+ chars) by adding \\\\?\\ prefix."""
    path_str = str(path_obj)
    if os.name == 'nt' and os.path.isabs(path_str) and not path_str.startswith('\\\\'):
        return '\\\\?' + os.path.sep + os.path.abspath(path_str)
    return path_str

def select_files(config, tag):
    """
    Update the selected file paths in the config.
    """
    folder_path_norm = _normalize_path(config.folder_path)
    if os.path.isdir(folder_path_norm):
        # config.file_list = sorted(glob.glob(os.path.join(config.folder_path, f"*{config.file_extensions}")))
        pattern = re.compile(f".*{config.file_extensions}$", re.IGNORECASE)
        config.file_list = natsorted([
            os.path.join(config.folder_path, entry.name)
            for entry in os.scandir(folder_path_norm)
            if entry.is_file() and pattern.search(entry.name)
        ])
        print(f"---- File list from [{tag}]:", config.file_list)
        if not config.file_list:
            config.file_list = ['[Error] No file found! Recheck the folder path or file extension, otherwise report the issue.']
    else:
        config.file_list = ['[Error] Folder path not found! Recheck the folder path or report the issue.']

def sync_file_list_checkboxes(config, tag):
    """
    Synchronize checkbox states for an existing file list widget without rebuilding it.
    """
    if not tag or not dpg.does_item_exist(tag):
        return

    selected_set = set(config.selected_files or [])
    for file in config.file_list:
        filename = os.path.basename(file)
        checkbox_tag = f"checkbox_{tag}_{filename}"
        if dpg.does_item_exist(checkbox_tag):
            dpg.set_value(checkbox_tag, filename in selected_set)

def update_selected_files(config, tag=None):
    """
    Update the list of selected files in config.selected_files.
    """
    config.selected_files = [os.path.basename(file) for file in config.file_list
                            if dpg.get_value(f"checkbox_{tag}_{os.path.basename(file)}")
                            ]
        
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
            sync_file_list_checkboxes(config, "child_window_file_list_eis")
        if dpg.does_item_exist("tab_bar_drt_plot_all"):
            gui_utils.drt_plots.update_all_plots(config)
            sync_file_list_checkboxes(config, "child_window_file_list_drt")
        if dpg.does_item_exist("tab_bar_cnls_plot_all"):
            gui_utils.cnls_plots.update_all_plots(config)
            sync_file_list_checkboxes(config, "child_window_file_list_cnls")
        sync_file_list_checkboxes(config, "child_window_file_list_soceis")
    except:
        print("[Warning] EIS/DRT/CNLS ALL-plots update failed. Please check the EIS/DRT/CNLS data, or come to file_list.update_seleted_files and check.")
    
    try:
        if dpg.does_item_exist("tab_eis") or dpg.does_item_exist("tab_drt") or dpg.does_item_exist("tab_cnls"):
            gui_utils.file_list.display_file(None, config.display_file, config)
    except:
        print("---- Tab not open.")
    
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

def _sync_selected_files_with_current_list(config):
    """Keep selected files valid after refreshing current folder-based file list."""
    valid_basenames = {os.path.basename(file) for file in config.file_list if "[Error]" not in file}
    config.selected_files = [name for name in (config.selected_files or []) if name in valid_basenames]
    config.display_file = config.selected_files[0] if config.selected_files else None

def _open_large_file_select_window(config, tag, EIS=None, CNLS=None):
    """Open a dedicated, larger window for selecting from current available file list."""
    window_tag = f"window_large_file_selector_{tag}"
    list_child_tag = f"child_large_selector_list_{tag}"
    index_input_tag = f"input_large_selector_index_{tag}"

    if dpg.does_item_exist(window_tag):
        dpg.delete_item(window_tag)

    # Ensure the list reflects current folder + extension.
    select_files(config, tag)
    current_file_names = [os.path.basename(path) for path in config.file_list if "[Error]" not in path]

    def _compress_one_based_indices(indices):
        ordered = sorted(set(indices))
        if not ordered:
            return ""

        ranges = []
        start = ordered[0]
        prev = ordered[0]
        for idx in ordered[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
                start = idx
                prev = idx
        ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
        return ",".join(ranges)

    def _selected_index_text_from_names(selected_names):
        index_map = {name: i for i, name in enumerate(current_file_names, start=1)}
        selected_indices = [index_map[name] for name in selected_names if name in index_map]
        return _compress_one_based_indices(selected_indices)

    def _update_temp_selected_from_window():
        selected_names = []
        for filename in current_file_names:
            cb_tag = f"checkbox_large_selector_{tag}_{filename}"
            if dpg.does_item_exist(cb_tag) and dpg.get_value(cb_tag):
                selected_names.append(filename)
        dpg.set_item_user_data(window_tag, selected_names)
        if dpg.does_item_exist(index_input_tag):
            dpg.set_value(index_input_tag, _selected_index_text_from_names(selected_names))

    def _on_confirm_add_files():
        _update_temp_selected_from_window()
        selected_names = dpg.get_item_user_data(window_tag) or []

        # Refresh by current folder + extension then apply selected filenames.
        select_files(config, tag)
        current_names = {os.path.basename(path) for path in config.file_list if "[Error]" not in path}
        config.selected_files = [name for name in selected_names if name in current_names]
        _sync_selected_files_with_current_list(config)

        update_file_list(config, tag, EIS, CNLS)
        # Reuse standard selection callback to update display file and redraw all related plots.
        update_selected_files(config, tag)
        dpg.delete_item(window_tag)

    def _apply_index_selection():
        raw_text = dpg.get_value(index_input_tag) if dpg.does_item_exist(index_input_tag) else ""
        if not raw_text:
            for filename in current_file_names:
                cb_tag = f"checkbox_large_selector_{tag}_{filename}"
                if dpg.does_item_exist(cb_tag):
                    dpg.set_value(cb_tag, False)
            _update_temp_selected_from_window()
            return

        chosen_indices = set()
        for token in str(raw_text).split(","):
            part = token.strip()
            if not part:
                continue
            if "-" in part:
                pieces = part.split("-", 1)
                try:
                    start = int(pieces[0].strip())
                    end = int(pieces[1].strip())
                except ValueError:
                    continue
                if start > end:
                    start, end = end, start
                for idx in range(start, end + 1):
                    chosen_indices.add(idx)
            else:
                try:
                    chosen_indices.add(int(part))
                except ValueError:
                    continue

        for one_based_idx, filename in enumerate(current_file_names, start=1):
            cb_tag = f"checkbox_large_selector_{tag}_{filename}"
            if dpg.does_item_exist(cb_tag):
                dpg.set_value(cb_tag, one_based_idx in chosen_indices)

        _update_temp_selected_from_window()

    viewport_width = dpg.get_viewport_client_width() if hasattr(dpg, "get_viewport_client_width") else dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_client_height() if hasattr(dpg, "get_viewport_client_height") else dpg.get_viewport_height()
    win_width = max(900, int(viewport_width * 0.75))
    win_height = max(620, int(viewport_height * 0.75))

    with dpg.window(
        label="Large File Selector",
        tag=window_tag,
        modal=True,
        width=win_width,
        height=win_height,
        no_resize=False,
        no_collapse=True,
    ):
        dpg.add_text("Select files from current available list, then confirm to apply.")
        dpg.add_separator()
        with dpg.child_window(tag=list_child_tag, width=-1, height=int(win_height * 0.78), horizontal_scrollbar=True):
            for filename in current_file_names:
                default_checked = filename in (config.selected_files or [])
                dpg.add_checkbox(
                    label=filename,
                    tag=f"checkbox_large_selector_{tag}_{filename}",
                    default_value=default_checked,
                    callback=lambda s, a: _update_temp_selected_from_window()
                )
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_text("Index")
            dpg.add_input_text(
                tag=index_input_tag,
                hint="e.g. 1,3,5-8",
                width=220,
                on_enter=True,
                callback=lambda s, a: _apply_index_selection(),
            )
            dpg.add_button(label="Apply Index", callback=lambda: _apply_index_selection())
        _update_temp_selected_from_window()
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Select all", callback=lambda: [dpg.set_value(f"checkbox_large_selector_{tag}_{name}", True) for name in current_file_names if dpg.does_item_exist(f"checkbox_large_selector_{tag}_{name}")] or _update_temp_selected_from_window())
            dpg.add_button(label="Unselect all", callback=lambda: [dpg.set_value(f"checkbox_large_selector_{tag}_{name}", False) for name in current_file_names if dpg.does_item_exist(f"checkbox_large_selector_{tag}_{name}")] or _update_temp_selected_from_window())
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Confirm", callback=_on_confirm_add_files)
            dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item(window_tag))

def update_file_list(config, tag = None, EIS = None, CNLS = None):
    """
    Update the file list based on the selected extension and default folder path.
    """
    config.file_extensions = dpg.get_value("file_extension_selector")
    select_files(config, tag)
    dpg.delete_item(tag, children_only=True)
    first_selected_file = os.path.basename(config.selected_files[0]) if config.selected_files else None

    with dpg.menu_bar(parent=tag):
        with dpg.menu(label="File list"):
            dpg.add_menu_item(label="Select all", callback=lambda: select_all_files(config, tag))
            dpg.add_menu_item(label="Unselect all", callback=lambda: unselect_all_files(config, tag))
            dpg.add_menu_item(label="Open large selector", callback=lambda: _open_large_file_select_window(config, tag, EIS, CNLS))

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
                label=gui_utils.small_functions.string_abbreviation(filename, 38, 38) if tag == "child_window_file_list_soceis" else gui_utils.small_functions.string_abbreviation(filename, 22, 22),
                tag=checkbox_tag,
                default_value=should_check,
                callback=lambda s, a, f=filename: update_selected_files(config, tag)
            )
        
        # Import all the data if there is historical data
            for idx, file in enumerate(config.file_list):
                file_name_no_ext = os.path.splitext(os.path.basename(file))[0]
                is_first_selected_file = first_selected_file is not None and os.path.basename(file) == first_selected_file
                if os.path.isdir(_normalize_path(os.path.join(config.folder_path, "EIS"))) and "[Error]" not in file and os.path.exists(_normalize_path(os.path.join(os.path.join(config.folder_path, "EIS"), file_name_no_ext+".xlsx"))):
                    if file_name_no_ext not in config.store.keys() or "EIS" not in config.store[file_name_no_ext].keys() or config.store[file_name_no_ext]['EIS'].raw['Re'] is None:
                        config.store[file_name_no_ext] = {}
                        config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_EIS()
                    
                        if is_first_selected_file or (config.selected_files is None and idx == 0):
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_EIS()
                            print(f"---- EIS data imported from {file} successfully.")
                
                if os.path.isdir(_normalize_path(os.path.join(config.folder_path, "DRT"))) and "[Error]" not in file and os.path.exists(_normalize_path(os.path.join(os.path.join(config.folder_path, "DRT"), file_name_no_ext+".xlsx"))):
                    if file_name_no_ext not in config.store.keys() or "EIS" not in config.store[file_name_no_ext].keys():
                        config.store[file_name_no_ext] = {}
                        config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_DRT()

                        if is_first_selected_file or (config.selected_files is None and idx == 0):
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_DRT()
                            print(f"---- DRT data imported from {file} successfully.")
                    elif config.store['beacon_DRT_import']:
                        EIS_tmp = config.store[file_name_no_ext]['EIS']
                        EIS_tmp.file_folder = config.folder_path
                        EIS_tmp.filename = os.path.basename(file)
                        EIS_tmp.import_data_DRT()

                        if is_first_selected_file or (config.selected_files is None and idx == 0):
                            EIS.file_folder = config.folder_path
                            EIS.filename = os.path.basename(file)
                            EIS.import_data_DRT()
                            print(f"---- DRT data imported from {file} successfully.")
                if os.path.isdir(_normalize_path(os.path.join(config.folder_path, "CNLS"))) and "[Error]" not in file and os.path.exists(_normalize_path(os.path.join(os.path.join(config.folder_path, "CNLS"), file_name_no_ext+".xlsx"))):
                    file_data = config.store.get(file_name_no_ext, {})
                    try:
                        if "CNLS" not in file_data:
                            if file_name_no_ext not in config.store.keys():
                                config.store[file_name_no_ext] = {}
                            if "ReIm" in config.store[file_name_no_ext]['EIS']['tknv_truncated'].keys():
                                config.store[file_name_no_ext]['CNLS'] = copy.deepcopy(Circuit(file_folder=config.folder_path, filename=os.path.basename(file), Elements = None, EIS = config.store[file_name_no_ext]['EIS'] if 'EIS' in config.store[file_name_no_ext].keys() and config.store[file_name_no_ext]['EIS'].tknv_truncated is not None else None, data_type = 'truncated'))
                                CNLS_tmp = config.store[file_name_no_ext]['CNLS']
                                CNLS_tmp.ImportCircuit()
                            else:
                                continue
                        
                            if is_first_selected_file or (config.selected_files is None and idx == 0):
                                CNLS.file_folder = config.folder_path
                                CNLS.filename = os.path.basename(file)
                                CNLS.ImportCircuit()
                                config.store["Elements"] = CNLS.Elements if CNLS.Elements is not None else {}
                                config.store["segment_constraints"] = CNLS.constraint_type
                                print(f"---- CNLS data imported from {file} successfully.")
                    except Exception as e:
                        print(f"[Warning] CNLS data import failed for {file}. Please check the CNLS and EIS data folder in the file. Error details: {e}")
                            
            config.store['beacon_DRT_import'] = False
    file_alignment(config)

def display_file(sender, app_data, config):
    """
    Callback function to display the selected file in the combo box.
    """
    # Update the displayed file name in the GUI
    if sender is not None:
        config.display_file = dpg.get_value(sender)
    else:
        config.display_file = app_data if app_data is not None else None

    EIS_tmp = config.store[os.path.splitext(config.display_file)[0]]['EIS'] if config.display_file and os.path.splitext(config.display_file)[0] in config.store.keys() and 'EIS' in config.store[os.path.splitext(config.display_file)[0]].keys() else None
    
    CNLS_tmp = config.store[os.path.splitext(config.display_file)[0]]['CNLS'] if config.display_file and os.path.splitext(config.display_file)[0] in config.store.keys() and 'CNLS' in config.store[os.path.splitext(config.display_file)[0]].keys() else None

    # Update EIS data
    try:
        # General parameters
        dpg.set_value("CellArea", f"{float(EIS_tmp.parameter["Sample"]["CellArea"]):.2f}")
        dpg.set_value("n_cell", f"{float(EIS_tmp.parameter['Sample']['n_cell']):.0f}")
        dpg.set_value("instrument_type", EIS_tmp.parameter['Sample']['instrument_type'])
        dpg.set_value("num_cut_upper", f"{float(EIS_tmp.parameter['Preprocessing']['num_cut_upper']):.0f}")
        dpg.set_value("num_cut_lower", f"{float(EIS_tmp.parameter['Preprocessing']['num_cut_lower']):.0f}")
        dpg.set_value("sig_threshold", f"{float(EIS_tmp.parameter['RM_significance']['sig_threshold']):.3f}")
        dpg.set_value("kk_threshold", f"{float(EIS_tmp.parameter['KK']['kk_threshold']):.1f}")
        dpg.set_value("rm_significance", EIS_tmp.parameter["RM_significance"]["rm_significance"])
        dpg.set_value("rm_outliers", EIS_tmp.parameter["Rmoutliers"]["Rmoutliers"])
        dpg.set_value("RmNonKK", EIS_tmp.parameter["KK"]["RmNonKK"])

        # KK parameters
        dpg.set_value("nRCmax", f"{float(EIS_tmp.parameter['KK']['nRCmax']):.0f}")
        dpg.set_value("nRC", f"{float(EIS_tmp.parameter['KK']['nRC']):.0f}")
        dpg.set_value("mu_threshold", f"{float(EIS_tmp.parameter['KK']['mu_threshold']):.2f}")
        dpg.set_value("KK_test", EIS_tmp.parameter["KK"]["KK_test"])
        dpg.set_value("KK_type", True if EIS_tmp.parameter["KK"]["KK_type"] == "Mu_criterion" else False)

        # Manual removal parameters
        dpg.set_value("checkbox_manual_remove_batch_points", EIS_tmp.parameter["ManualRemoval"]["enable"])
        dpg.set_value("input_manual_remove_batch_indices", gui_utils.eis_batch_manual.compress_indices([i+1 for i in EIS_tmp.parameter["ManualRemoval"]["indices"]]))

        # EIS parameters
        dpg.set_value("Smooth_PointsPerDecade", f"{float(EIS_tmp.parameter['Smoothing']['PointsPerDecade']):.0f}")
        dpg.set_value("extrapolation_fmin", f"{float(EIS_tmp.parameter['Extrapolation']['fmin']):.0e}")
        dpg.set_value("extrapolation_fmax", f"{float(EIS_tmp.parameter['Extrapolation']['fmax']):.0e}")
        dpg.set_value("Extrapolation_PointsPerDecade", f"{float(EIS_tmp.parameter['Extrapolation']['PointsPerDecade']):.0f}")
        dpg.set_value("zhit_enable", EIS_tmp.parameter["ZHIT"]["enable"])
        dpg.set_value("zhit_poly_order", f"{float(EIS_tmp.parameter['ZHIT']['poly_order']):.0f}")
        dpg.set_value("zhit_window_frac", f"{float(EIS_tmp.parameter['ZHIT']['window_frac']):.3f}")

        # Enable stuff
        dpg.configure_item("num_cut_upper", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("num_cut_lower", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("sig_threshold", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("kk_threshold", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("rm_significance", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("rm_outliers", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("RmNonKK", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("button_manual_cut_single", enabled=not EIS_tmp.parameter['ManualRemoval']['enable'])

        dpg.configure_item("input_manual_remove_batch_indices", enabled=EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("button_manual_cut_batch", enabled=EIS_tmp.parameter['ManualRemoval']['enable'])
        dpg.configure_item("button_manual_cut_batch_reset", enabled=EIS_tmp.parameter['ManualRemoval']['enable'])

    except Exception as e:
        print(f"[Warning] setting EIS parameters: {e} for displayed file.")

    # Update DRT parameters
    try:
        dpg.set_value('check_box_tknv_pos', EIS_tmp.parameter["DRT"]["tknv_pos"])
        dpg.set_value('input_text_lambda', EIS_tmp.parameter["DRT"]["lambda"])
        dpg.set_value('input_text_min_lambda', EIS_tmp.parameter["LambdaOpt"]["lambda_min"])
        dpg.set_value('input_text_max_lambda', EIS_tmp.parameter["LambdaOpt"]["lambda_max"])
        dpg.set_value('input_text_lambda_points', EIS_tmp.parameter["LambdaOpt"]["n"])
        if dpg.does_item_exist('combo_lambda_target'):
            lambda_target_items = gui_utils.drt_functions.get_lambda_target_items(EIS_tmp)
            dpg.configure_item('combo_lambda_target', items=lambda_target_items)
            lambda_target = gui_utils.drt_functions.normalize_lambda_target(
                EIS_tmp.parameter["LambdaOpt"].get("target", "truncated"),
                EIS_tmp,
            )
            EIS_tmp.parameter["LambdaOpt"]["target"] = lambda_target
            dpg.set_value('combo_lambda_target', lambda_target)
        lambda_mode_optimal = EIS_tmp.parameter["DRT"].get("Lambda_selection", "Manual") == "Optimal"
        if dpg.does_item_exist('check_box_lambda_mode'):
            dpg.set_value('check_box_lambda_mode', lambda_mode_optimal)
        if dpg.does_item_exist("input_text_lambda"):
            dpg.configure_item("input_text_lambda", enabled=not lambda_mode_optimal)
            dpg.set_value("input_text_lambda", "Optimal" if lambda_mode_optimal else EIS_tmp.parameter["DRT"]["lambda"])
        if dpg.does_item_exist("text_optimal_lambda") and config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt:
            dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.4e}")
        elif dpg.does_item_exist("text_optimal_lambda"):
            dpg.set_value("text_optimal_lambda", "Non-calculated")
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
            dpg.configure_item("input_nbr_peaks", default_value = len(config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_fixed)) if config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_fixed is not None else 6
            gui_utils.cnls_functions.dynamic_peak_ids(0, 0, config)
            gui_utils.cnls_table.table_update(config)
            gui_utils.cnls_plots.update_single_plots(config)
            if config.store["Elements"] is None or config.store["Elements"] == []:
                config.store["Elements"] = [
                            {'name': 'L1', 'type': 'Inductor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
                            {'name': 'R2', 'type': 'Resistor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
                        ]
            if config.store[os.path.splitext(config.display_file)[0]]['CNLS'].Elements is not None:
                config.store["Elements"] = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].Elements
            gui_utils.cnls_elements.update_elements(config)
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
        default_value = gui_utils.small_functions.string_abbreviation(config.display_file, 17, 17) if config.display_file is not None else None,
        width = -1,
        items=config.selected_files,
        callback=lambda s, a: gui_utils.file_list.display_file(s, a, config)
    )

def file_alignment(config):
    """
    Align the file list and display file in the GUI.
    """
    # Iterate through the file list and check for alignment
    print("-- File alignment check:")
    if '[Error]' not in config.file_list[0]:
        # Check files in EIS folder for alignment with config.file_list
        eis_folder = os.path.join(config.folder_path, "EIS")
        if os.path.isdir(eis_folder):
            for existing_file in glob.glob(os.path.join(eis_folder, "*.xlsx")):
                file_name_no_ext = os.path.splitext(os.path.basename(existing_file))[0]
                if file_name_no_ext not in [os.path.splitext(os.path.basename(f))[0] for f in config.file_list]:
                    print(f"[Warning] unaligned file in EIS: {existing_file}")

        # Check files in DRT folder for alignment with config.file_list
        drt_folder = os.path.join(config.folder_path, "DRT")
        if os.path.isdir(drt_folder):
            for existing_file in glob.glob(os.path.join(drt_folder, "*.xlsx")):
                file_name_no_ext = os.path.splitext(os.path.basename(existing_file))[0]
                if file_name_no_ext not in [os.path.splitext(os.path.basename(f))[0] for f in config.file_list]:
                    print(f"[Warning] unaligned file in DRT: {existing_file}")

        # Check files in CNLS folder for alignment with config.file_list
        cnls_folder = os.path.join(config.folder_path, "CNLS")
        if os.path.isdir(cnls_folder):
            for existing_file in glob.glob(os.path.join(cnls_folder, "*.xlsx")):
                file_name_no_ext = os.path.splitext(os.path.basename(existing_file))[0]
                if file_name_no_ext not in [os.path.splitext(os.path.basename(f))[0] for f in config.file_list]:
                    print(f"[Warning] unaligned file in CNLS: {existing_file}")

        # Ensure all files in config.selected_files exist in the target folders
        aligned_selected_files = []
        file_list_base_names = [os.path.basename(file) for file in config.file_list]

        for file_name in config.selected_files:
            if file_name in file_list_base_names:
                aligned_selected_files.append(file_name)
            else:
                print(f"[Warning] unaligned file in selected_files: {file_name}")

        # Update config.selected_files with the aligned list
        config.selected_files = aligned_selected_files
    print("---- File alignment finished.")
