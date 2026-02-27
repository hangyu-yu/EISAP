import os
import glob
import numpy as np
import pandas as pd
from pathlib import Path
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg

def _get_manualcut_preview_data(config):
    """
    Preview for selector = RAW after ONLY upper/lower cut.
    No significance/outlier/KK/manual removal are applied here.

    This keeps selector indices stable and avoids misleading visuals.
    """
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    f = np.asarray(EIS_tmp.truncated["f"], dtype=float)
    Re = np.asarray(EIS_tmp.truncated["Re"], dtype=float)
    Im = np.asarray(EIS_tmp.truncated["Im"], dtype=float)

    return f, Re, Im

def parse_indices_1based_to_0based(text: str):
    if text is None:
        return []
    s = str(text).strip()
    if s == "" or s.lower() in {"n/a", "na", "none"}:
        return []

    out = []
    for token in s.replace(" ", "").split(","):
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            if a.isdigit() and b.isdigit():
                a, b = int(a), int(b)
                lo, hi = (a, b) if a <= b else (b, a)
                out.extend([i - 1 for i in range(lo, hi + 1) if i > 0])
        else:
            if token.isdigit():
                v = int(token)
                if v > 0:
                    out.append(v - 1)

    return sorted(set(out))

def open_manual_cut_window(config):
    if config.display_file in (None, "", []):
        return

    file_key = os.path.splitext(config.display_file)[0]
    if file_key not in config.store or "EIS" not in config.store[file_key]:
        return

    # close old one
    if dpg.does_item_exist("manual_cut_window"):
        close_manual_cut_window()

    # preview arrays
    f, Re, Im = _get_manualcut_preview_data(config)
    if f is None or len(f) == 0:
        return

    Re = np.asarray(Re, dtype=float)
    Im = np.asarray(Im, dtype=float)
    f = np.asarray(f, dtype=float)

    prev = set(config.store[file_key]["EIS"].parameter.get("ManualRemoval", {}).get("indices", []) or [])

    # helpers
    def _selected_indices_from_checks(n):
        sel = []
        for i in range(n):
            tag = f"manual_remove_chk_{i}"
            if dpg.does_item_exist(tag) and dpg.get_value(tag):
                sel.append(i)
        return sel

    def _update_plot():
        n = len(f)
        sel = set(_selected_indices_from_checks(n))

        keep_mask = np.ones(n, dtype=bool)
        if sel:
            keep_mask[list(sel)] = False

        # kept points
        kept_x = Re[keep_mask].tolist()
        kept_y = (-Im[keep_mask]).tolist()

        # removed points
        rem_mask = ~keep_mask
        rem_x = Re[rem_mask].tolist()
        rem_y = (-Im[rem_mask]).tolist()

        # update series data
        if dpg.does_item_exist("manual_cut_series_kept"):
            dpg.set_value("manual_cut_series_kept", [kept_x, kept_y])
        if dpg.does_item_exist("manual_cut_series_removed"):
            dpg.set_value("manual_cut_series_removed", [rem_x, rem_y])

    def _on_row_toggle(sender, app_data, user_data):
        # live update when checkbox toggled
        _update_plot()

    def _hover():
        if not dpg.is_item_hovered("manual_cut_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()  # plot coordinates

        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        dpg.set_value(
            "manual_cut_hover_text",
            f"Hover -> Index: {idx+1} | f: {f[idx]:.3e} Hz | Re: {Re[idx]:.3e} | Im: {Im[idx]:.3e}"
        )
        
    def _toggle_nearest_point():
        if not dpg.is_item_hovered("manual_cut_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()
        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        tag = f"manual_remove_chk_{idx}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, not dpg.get_value(tag))
            _update_plot()


    # ---- build window (no context managers) ----
    dpg.add_window(
        tag="manual_cut_window",
        label="Manual Point Removal: "+ config.display_file,
        modal=True,
        width=1200,
        height=700,
        no_collapse=True,
        no_resize=False
    )

    dpg.add_group(parent="manual_cut_window", tag="manual_cut_group", horizontal=True)
    dpg.add_child_window(parent="manual_cut_group", tag="manual_cut_left", width=560, height=-55, border=True)
    dpg.add_child_window(parent="manual_cut_group", tag="manual_cut_right", width=-1, height=-55, border=True)

    # ---- TABLE ----
    dpg.add_table(
        parent="manual_cut_left",
        tag="manual_cut_table",
        header_row=True,
        resizable=True,
        scrollX=True,
        scrollY=True,
        borders_innerV=True,
        borders_outerV=True,
        borders_outerH=True,
        policy=dpg.mvTable_SizingFixedFit,
        height=-1
    )

    dpg.add_table_column(parent="manual_cut_table", label="Remove", width_fixed=True, init_width_or_weight=70)
    dpg.add_table_column(parent="manual_cut_table", label="Index",  width_fixed=True, init_width_or_weight=60)
    dpg.add_table_column(parent="manual_cut_table", label="Freq [Hz]", width_fixed=True, init_width_or_weight=150)
    dpg.add_table_column(parent="manual_cut_table", label="Re", width_fixed=True, init_width_or_weight=130)
    dpg.add_table_column(parent="manual_cut_table", label="Im", width_fixed=True, init_width_or_weight=130)

    for i in range(len(f)):
        row = f"manual_cut_row_{i}"
        dpg.add_table_row(parent="manual_cut_table", tag=row)

        dpg.add_checkbox(
            parent=row,
            tag=f"manual_remove_chk_{i}",
            default_value=(i in prev),
            callback=_on_row_toggle
        )

        dpg.add_text(parent=row, default_value=str(i + 1))
        dpg.add_text(parent=row, default_value=f"{float(f[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Re[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Im[i]):.6e}")

    # ---- PLOT ----
    dpg.add_plot(parent="manual_cut_right", tag="manual_cut_plot", width=-1, height=-1, no_menus=False, equal_aspects = True)
    dpg.add_plot_axis(dpg.mvXAxis, parent="manual_cut_plot", tag="manual_cut_x", label="Z' [Ohm·cm2]")
    dpg.add_plot_axis(dpg.mvYAxis, parent="manual_cut_plot", tag="manual_cut_y", label="-Z'' [Ohm·cm2]")

    # We create two scatter series and then update them live
    dpg.add_scatter_series([], [], parent="manual_cut_y", tag="manual_cut_series_kept", label="Kept")
    dpg.add_scatter_series([], [], parent="manual_cut_y", tag="manual_cut_series_removed", label="Removed")
    dpg.add_plot_legend(parent="manual_cut_plot")

    dpg.add_text(parent="manual_cut_right", default_value="Hover -> Index: -", tag="manual_cut_hover_text")

    # handler for hover
    if dpg.does_item_exist("manual_cut_handlers"):
        dpg.delete_item("manual_cut_handlers")
    dpg.add_handler_registry(tag="manual_cut_handlers")
    dpg.add_mouse_move_handler(parent="manual_cut_handlers", callback=lambda s, a: _hover())

    dpg.add_mouse_click_handler(
        parent="manual_cut_handlers",
        button=dpg.mvMouseButton_Left,
        callback=lambda s, a: _toggle_nearest_point()
    )

    # initial plot update (reflect prev selection)
    _update_plot()

    # ---- Buttons ----
    dpg.add_separator(parent="manual_cut_window")
    dpg.add_group(parent="manual_cut_window", tag="manual_cut_buttons", horizontal=True)

    dpg.add_button(
        parent="manual_cut_buttons",
        label="Process manually-cut data",
        callback=lambda: process_manually_cut_data(config, len(f))
    )
    dpg.add_button(
        parent="manual_cut_buttons",
        label="Cancel",
        callback=lambda: close_manual_cut_window()
    )

def close_manual_cut_window():
    if dpg.does_item_exist("manual_cut_handlers"):
        dpg.delete_item("manual_cut_handlers")
    if dpg.does_item_exist("manual_cut_window"):
        dpg.delete_item("manual_cut_window")

def process_manually_cut_data(config, n_points_preview):
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    indices = []
    for i in range(n_points_preview):
        if dpg.does_item_exist(f"manual_remove_chk_{i}") and dpg.get_value(f"manual_remove_chk_{i}"):
            indices.append(i)  # 0-based relative to the preview array

    close_manual_cut_window()
    n = len(EIS_tmp.truncated["f"])
    if indices:
        mask = np.ones(n, dtype=bool)
        mask[indices] = False
        for key in EIS_tmp.truncated.keys():
            if EIS_tmp.truncated[key] is not None:
                EIS_tmp.truncated[key] = np.asarray(EIS_tmp.truncated[key])[mask]

    # 05 - KK test
    if EIS_tmp.parameter['KK']['KK_test']:
        EIS_tmp.KK_test(EIS_tmp.truncated)
    
    # 06 - Data cut based on KK residual
    if EIS_tmp.parameter['KK']['RmNonKK']:
        EIS_tmp.rm_auto_KK()
        EIS_tmp.KK_test(EIS_tmp.truncated)
    
    # 06 - Get smoothed data, LCcorrected data, and extrapolated data
    EIS_tmp.parameter['Smoothing']['fmax'] = max(EIS_tmp.truncated['f'])
    EIS_tmp.parameter['Smoothing']['fmin'] = min(EIS_tmp.truncated['f'])
    EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
    EIS_tmp.store['RsLCinv_kk']['L'] = 0
    EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0
    EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
    EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

    # Update figures and tables
    gui_utils.eis_table.table_update(config)
    gui_utils.eis_plots.update_single_plots(config)
    gui_utils.eis_plots.update_all_plots(config)

# Callback function to handle the options
def update_child_window_size():
    """
    Update the size of the child window based on the viewport size.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the width and height of the child window
    dpg.configure_item("child_window_file_list_eis", width=int(viewport_width * 0.33), height=int(viewport_height * 0.2))
    dpg.configure_item("child_window_parameter_eis", width=int(viewport_width * 0.33), height=int(viewport_height * 0.285))
    dpg.configure_item("child_window_eis_buttons", width=int(viewport_width * 0.33), height=int(viewport_height * 0.082))
    dpg.configure_item("child_window_eis_data", width=int(viewport_width * 0.33), height=-1)
    dpg.configure_item("child_window_eis_plot", width=-1, height=-1)
    dpg.configure_item("Button_data_import", width=int(viewport_width*0.075))
    dpg.configure_item("Button_drt_Process_dataters", width=int(viewport_width*0.075))
    dpg.configure_item("Button_Process_data", width=int(viewport_width*0.075))
    dpg.configure_item("Button_Save_EIS", width=-1)

def rm_significance_callback(sender, app_data, EIS):
    # Get the current value of the checkbox
    EIS.parameter["RM_significance"]["rm_significance"] = dpg.get_value(sender)
    
    # Print the updated value for debugging
    print(f"Remove low significance values: {EIS.parameter['RM_significance']['rm_significance']}")

def rm_outliers_callback(sender, app_data, EIS):
    # Get the current value of the checkbox
    EIS.parameter["Rmoutliers"]["Rmoutliers"] = dpg.get_value(sender)
    
    # Print the updated value for debugging
    print(f"Rmove outliers: {EIS.parameter['Rmoutliers']['Rmoutliers']}")

def KK_test_callback(sender, app_data, EIS):
    # Get the current value of the checkbox
    EIS.parameter["KK"]["KK_test"] = dpg.get_value(sender)

    # Control the enabled state of the other KK checkboxes
    dpg.configure_item("KK_type", enabled=app_data)
    dpg.configure_item("RmNonKK", enabled=app_data)
    
    # Print the updated value for debugging
    print(f"KK test: {EIS.parameter['KK']['KK_test']}")

def KK_type_callback(sender, app_data, EIS):
    # Get the current value of the checkbox
    checkbox_value = dpg.get_value(sender)
    # Update the EIS parameter based on the checkbox value
    if checkbox_value:
        EIS.parameter["KK"]["KK_type"] = 'Mu_criterion'
    else:
        EIS.parameter["KK"]["KK_type"] = 'standard'
    
    # Print the updated value for debugging
    print(f"Checkbox State: {checkbox_value}, KK_type: {EIS.parameter['KK']['KK_type']}")

def RmNonKK_callback(sender, app_data, EIS):
    # Get the current value of the checkbox
    EIS.parameter["KK"]["RmNonKK"] = dpg.get_value(sender)
    
    # Print the updated value for debugging
    print(f"RmNonKK: {EIS.parameter['KK']['RmNonKK']}")


# Functions for file dialog callbacks
def file_selector_ok_callback(sender, app_data, config):
    """
    Callback function when directory is selected in file dialog.
    """
    print('OK was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)
    config.data_import_function = app_data['file_path_name']
    print("Import function path:", config.data_import_function)
    dpg.set_value("function_import", os.path.basename(config.data_import_function))

def file_selector_cancel_callback(sender, app_data):
    """
    Callback function when file dialog is cancelled.
    """
    print('Cancel was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)

def callback_process_data(sender, app_data, EIS, config):
    """
    Callback function to process and update EIS data in the GUI.
    """
    gui_utils.eis_functions.process_data(sender, app_data, config, EIS)
    gui_utils.eis_table.table_update(config)
    gui_utils.eis_plots.update_single_plots(config)
    gui_utils.eis_plots.update_all_plots(config)

# Main tab function for EIS
def gui_tab_eis(config, EIS, CNLS):
    config.save_config()
    dpg.delete_item("file_dialog_eis")  # Delete the tab bar if it already exists
    dpg.delete_item("tab_eis", children_only=False)  # Delete the tab if it already exists
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the theme for different widgets
    with dpg.theme() as blue_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135, 255))  # Background color (blue)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))  # Text color (white)

    with dpg.tab(label="EIS", tag="tab_eis", parent="tab_bar_main"):
        with dpg.group(horizontal=True):
            with dpg.group():
                # Window for file list
                with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.2), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_eis"):
                    gui_utils.file_list.update_file_list(config, "child_window_file_list_eis", EIS, CNLS)

                # Window for the parameters
                with dpg.child_window(width=int(viewport_width * 0.33), height=int(viewport_height * 0.285), horizontal_scrollbar=True, menubar=True, tag="child_window_parameter_eis"):
                    with dpg.menu_bar(parent="child_window_parameter_eis"):
                        with dpg.menu(label="Parameters"):
                            dpg.add_menu_item(label="")
                    with dpg.tab_bar(tag="tab_bar_eis_parameters"):
                        # Sample parameters
                        with dpg.tab(label="General", tag="tab_eis_parameter_general"):
                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):
                                # Two columns for the sample name and the sample type
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))
                                
                                # Table content
                                with dpg.table_row():
                                    dpg.add_text("Cell area [cm²]:", tag="text_CellArea")
                                    dpg.add_input_text(tag="CellArea", default_value=EIS.parameter["Sample"]["CellArea"])
                                    dpg.add_checkbox(
                                        tag="rm_significance",
                                        label="Remove low sig. data",
                                        callback=lambda sender, app_data: rm_significance_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("Cell No.:", tag="text_n_cell")
                                    dpg.add_input_text(tag="n_cell", default_value=EIS.parameter["Sample"]["n_cell"])
                                    dpg.add_checkbox(
                                        tag="rm_outliers",
                                        label="Remove outliers",
                                        default_value=EIS.parameter["Rmoutliers"]["Rmoutliers"],
                                        callback=lambda sender, app_data: rm_outliers_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("Instrument", tag="text_instrument_type")
                                    dpg.add_input_text(tag="instrument_type", default_value=EIS.parameter["Sample"]["instrument_type"])
                                    with dpg.file_dialog(
                                        directory_selector=False, 
                                        show=False, 
                                        default_path= os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Functions", "01_Data_read"),
                                        callback=lambda sender, app_data: file_selector_ok_callback(sender, app_data, config),
                                        tag="file_dialog_eis",
                                        cancel_callback=lambda sender, app_data: file_selector_cancel_callback(sender, app_data),
                                        width=700,
                                        height=400):
                                        dpg.add_file_extension(".py", color=(0, 255, 0, 255), custom_text="[Python]")
                                    dpg.add_checkbox(
                                        tag="RmNonKK",
                                        label="Remove high KK residual data",
                                        default_value= EIS.parameter["KK"]["RmNonKK"],
                                        callback=lambda sender, app_data: RmNonKK_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("Upper cut:", tag="text_num_cut_upper")
                                    dpg.add_input_text(tag="num_cut_upper", default_value=EIS.parameter["Preprocessing"]["num_cut_upper"])
                                    dpg.add_button(
                                        label="Data import function",
                                        callback=lambda: dpg.show_item("file_dialog_eis"),
                                        tag="button_data_import_function"
                                    )
                                    dpg.bind_item_theme("button_data_import_function", blue_button_theme)
                                with dpg.table_row():
                                    dpg.add_text("Lower cut:", tag="text_num_cut_lower")
                                    dpg.add_input_text(tag="num_cut_lower", default_value=EIS.parameter["Preprocessing"]["num_cut_lower"])
                                    if config.data_import_function:
                                        data_import_function_text = os.path.basename(config.data_import_function)
                                    else:
                                        data_import_function_text = "No function selected"
                                    dpg.add_text(data_import_function_text, tag="function_import")
                                with dpg.table_row():
                                    dpg.add_text("Min significance:", tag="text_sig_threshold")
                                    dpg.add_input_text(tag="sig_threshold", default_value=EIS.parameter["RM_significance"]["sig_threshold"])
                                    dpg.add_button(
                                        label="Manual cut & Process",
                                        callback=lambda s, a: open_manual_cut_window(config)
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Max. KK res. [%]")
                                    dpg.add_input_text(tag="kk_threshold", default_value=EIS.parameter["KK"]["kk_threshold"])

                        # Kramers–Kronig test parameters
                        with dpg.tab(label="Kramers Kronig", tag="tab_eis_parameter_KK"):
                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):
                                # Define the columns
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))

                                # Table content
                                with dpg.table_row():
                                    dpg.add_text("Max. RCs")
                                    dpg.add_input_text(tag="nRCmax", default_value=EIS.parameter["KK"]["nRCmax"])
                                    dpg.add_checkbox(
                                        tag="KK_test",
                                        label="KK_test",
                                        default_value= True,
                                        callback=lambda sender, app_data: KK_test_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("No. RC")
                                    dpg.add_input_text(tag="nRC", default_value=EIS.parameter["KK"]["nRC"])
                                    dpg.add_checkbox(
                                        tag="KK_type",
                                        label="Mu criterion",
                                        default_value= True,
                                        callback=lambda sender, app_data: KK_type_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("MU threshold")
                                    dpg.add_input_text(tag="mu_threshold", default_value=EIS.parameter["KK"]["mu_threshold"])    
                        
                        # EIS parameters
                        with dpg.tab(label="EIS", tag="tab_eis_parameter_EIS"):
                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):
                                # Define the columns
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))

                                # Table content
                                with dpg.table_row():
                                    dpg.add_text("Smooth PPD")
                                    dpg.add_input_text(tag="Smooth_PointsPerDecade", default_value=EIS.parameter["Smoothing"]["PointsPerDecade"])
                                with dpg.table_row():
                                    dpg.add_text("Ex. fmin [Hz]")
                                    dpg.add_input_text(tag="extrapolation_fmin", default_value=EIS.parameter["Extrapolation"]["fmin"])
                                with dpg.table_row():
                                    dpg.add_text("Ex. fmax [Hz]")
                                    dpg.add_input_text(tag="extrapolation_fmax", default_value=f"{EIS.parameter['Extrapolation']['fmax']:.0e}"
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Extrap. PPD")
                                    dpg.add_input_text(tag="Extrapolation_PointsPerDecade", default_value=EIS.parameter["Extrapolation"]["PointsPerDecade"])

                # Window for the buttons
                with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.082), horizontal_scrollbar=True, menubar=False, tag="child_window_eis_buttons"):
                    with dpg.group(horizontal=True):
                        dpg.add_button(tag="Button_data_import", label="Data import", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.eis_functions.data_import(s, a, config, EIS))
                        dpg.bind_item_theme("Button_data_import", blue_button_theme)

                        dpg.add_button(tag="Button_drt_Process_dataters", label="Load parameters", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.eis_functions.load_parameters(s, a, config, EIS))
                        dpg.bind_item_theme("Button_drt_Process_dataters", blue_button_theme)

                        dpg.add_button(tag="Button_Process_data", label="Process data", width=int(viewport_width*0.075), callback=lambda s, a: callback_process_data(s, a, EIS, config))
                        dpg.bind_item_theme("Button_Process_data", blue_button_theme)

                        dpg.add_button(tag="Button_Save_EIS", label="Save EIS", width=-1, callback=lambda s, a: gui_utils.eis_functions.save_eis(s, a, config))
                        dpg.bind_item_theme("Button_Save_EIS", blue_button_theme)
                        
                    with dpg.group(horizontal=True, tag="group_eis_display_file"):
                        dpg.add_text("Displayed file:")
                        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_eis_plot_file", "group_eis_display_file")
                
                # Window for the data display
                with dpg.child_window(width=int(viewport_width*0.33), height=-1, horizontal_scrollbar=True, menubar=False, border=False, tag="child_window_eis_data"):
                    with dpg.tab_bar(tag="tab_bar_eis_data"):
                        gui_utils.eis_table.table_update(config)

            # Window for the plot display
            with dpg.child_window(width=-1, height=-1, horizontal_scrollbar=True, menubar=False, border=True, tag="child_window_eis_plot"):
                with dpg.tab_bar(tag="tab_bar_eis_plot"):
                    with dpg.tab(label="Single", tag="tab_eis_plot_single"):
                        with dpg.tab_bar(tag="tab_bar_eis_plot_single"):
                            gui_utils.eis_plots.update_single_plots(config)
                    with dpg.tab(label="All", tag="tab_eis_plot_all"):
                        with dpg.tab_bar(tag="tab_bar_eis_plot_all"):
                            gui_utils.eis_plots.update_all_plots(config)
    # Update the child window size when the viewport is resized
    dpg.set_value("tab_bar_main", 'tab_eis')
    dpg.set_viewport_resize_callback(update_child_window_size)

                            