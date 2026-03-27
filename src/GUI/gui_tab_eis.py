import os
import glob
import numpy as np
import pandas as pd
from pathlib import Path
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg

# Callback function to handle the options
def update_child_window_size():
    """
    Update the size of the child window based on the viewport size.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    def safe_configure(tag, **kwargs):
        if dpg.does_item_exist(tag):
            dpg.configure_item(tag, **kwargs)
    
    # Set the width and height of the child window
    safe_configure("child_window_file_list_eis", width=int(viewport_width * 0.33), height=int(viewport_height * 0.2))
    safe_configure("child_window_parameter_eis", width=int(viewport_width * 0.33), height=int(viewport_height * 0.285))
    safe_configure("child_window_eis_buttons", width=int(viewport_width * 0.33), height=int(viewport_height * 0.082))
    safe_configure("child_window_eis_data", width=int(viewport_width * 0.33), height=-1)
    safe_configure("child_window_eis_plot", width=-1, height=-1)
    safe_configure("Button_data_import", width=int(viewport_width*0.075))
    safe_configure("Button_drt_Process_dataters", width=int(viewport_width*0.075))
    safe_configure("Button_Process_data", width=int(viewport_width*0.075))
    safe_configure("Button_Save_EIS", width=-1)

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

def manual_removal_callback(sender, app_data, config, EIS):
    # Get the current value of the checkbox
    EIS.parameter["ManualRemoval"]["Enable"] = dpg.get_value(sender)
    
    # Print the updated value for debugging
    if app_data:
        print(f"---- Manual removal enabled: {EIS.parameter['ManualRemoval']['enable']}, set the autocut to not working.")
        dpg.configure_item("num_cut_upper", enabled=False)
        dpg.configure_item("num_cut_lower", enabled=False)
        dpg.configure_item("sig_threshold", enabled=False)
        dpg.configure_item("kk_threshold", enabled=False)
        dpg.configure_item("rm_significance", enabled=False)
        dpg.configure_item("rm_outliers", enabled=False)
        dpg.configure_item("RmNonKK", enabled=False)
        dpg.configure_item("button_manual_cut_single", enabled=False)
        # Enable the complete manual cut
        dpg.configure_item("input_manual_remove_batch_indices", enabled=True)
        dpg.configure_item("button_manual_cut_batch", enabled=True)
        dpg.configure_item("button_manual_cut_batch_reset", enabled=True)
    else:
        print(f"---- Manual removal disabled: {EIS.parameter['ManualRemoval']['enable']}, set the autocut to working.")
        dpg.configure_item("num_cut_upper", enabled=True)
        dpg.configure_item("num_cut_lower", enabled=True)
        dpg.configure_item("sig_threshold", enabled=True)
        dpg.configure_item("kk_threshold", enabled=True)
        dpg.configure_item("rm_significance", enabled=True)
        dpg.configure_item("rm_outliers", enabled=True)
        dpg.configure_item("RmNonKK", enabled=True)
        dpg.configure_item("button_manual_cut_single", enabled=True)
        # Disable the complete manual cut
        dpg.configure_item("input_manual_remove_batch_indices", enabled=False)
        dpg.configure_item("button_manual_cut_batch", enabled=False)
        dpg.configure_item("button_manual_cut_batch_reset", enabled=False)

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

    # Fast path: if EIS tab already exists, just switch to it and avoid expensive rebuild.
    if dpg.does_item_exist("tab_eis"):
        dpg.set_value("tab_bar_main", "tab_eis")
        try:
            gui_utils.file_list.display_file(
                None,
                config.display_file,
                config,
                refresh_eis_tab=True,
                refresh_drt_tab=False,
                refresh_cnls_tab=False,
            )
        except Exception:
            pass
        update_child_window_size()
        return

    if dpg.does_item_exist("file_dialog_eis"):
        dpg.delete_item("file_dialog_eis")

    if dpg.does_item_exist("tab_eis"):
        dpg.delete_item("tab_eis", children_only=False)
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
                    gui_utils.file_list.update_file_list(
                        config,
                        "child_window_file_list_eis",
                        EIS,
                        CNLS,
                        import_history=False,
                        show_progress=False,
                        run_alignment=False,
                    )

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
                                        default_value=EIS.parameter["RM_significance"]["rm_significance"],
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        callback=lambda sender, app_data: rm_significance_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("Cell No.:", tag="text_n_cell")
                                    dpg.add_input_text(tag="n_cell", default_value=EIS.parameter["Sample"]["n_cell"])
                                    dpg.add_checkbox(
                                        tag="rm_outliers",
                                        label="Remove outliers",
                                        default_value=EIS.parameter["Rmoutliers"]["Rmoutliers"],
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        callback=lambda sender, app_data: rm_outliers_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("Instrument", tag="text_instrument_type")
                                    dpg.add_input_text(tag="instrument_type", default_value=EIS.parameter["Sample"]["instrument_type"])
                                    dpg.add_checkbox(
                                        tag="RmNonKK",
                                        label="Remove high KK residual data",
                                        default_value= EIS.parameter["KK"]["RmNonKK"],
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        callback=lambda sender, app_data: RmNonKK_callback(sender, app_data, EIS))
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
                                with dpg.table_row():
                                    dpg.add_text("Upper cut:", tag="text_num_cut_upper")
                                    dpg.add_input_text(
                                        tag="num_cut_upper", 
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        default_value=EIS.parameter["Preprocessing"]["num_cut_upper"]
                                        )
                                    dpg.add_button(
                                        label="Data import function",
                                        callback=lambda: dpg.show_item("file_dialog_eis"),
                                        tag="button_data_import_function"
                                    )
                                    dpg.bind_item_theme("button_data_import_function", blue_button_theme)
                                with dpg.table_row():
                                    dpg.add_text("Lower cut:", tag="text_num_cut_lower")
                                    dpg.add_input_text(
                                        tag="num_cut_lower", 
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        default_value=EIS.parameter["Preprocessing"]["num_cut_lower"]
                                        )
                                    if config.data_import_function:
                                        data_import_function_text = os.path.basename(config.data_import_function)
                                    else:
                                        data_import_function_text = "No function selected"
                                    dpg.add_text(data_import_function_text, tag="function_import")
                                with dpg.table_row():
                                    dpg.add_text("Min significance:", tag="text_sig_threshold")
                                    dpg.add_input_text(
                                        tag="sig_threshold", 
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        default_value=EIS.parameter["RM_significance"]["sig_threshold"])
                                    dpg.add_button(
                                        tag="button_manual_cut_single",
                                        label="Manual cut & Process",
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        callback=lambda s, a: gui_utils.eis_single_manual.open_manual_cut_window(config)
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Max. KK res. [%]")
                                    dpg.add_input_text(
                                        tag="kk_threshold", 
                                        enabled=not EIS.parameter["ManualRemoval"]["enable"],
                                        default_value=EIS.parameter["KK"]["kk_threshold"])

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

                                # Kramers-Kronig Analysis Parameters
                                with dpg.table_row():
                                    dpg.add_text("Max. RCs")
                                    dpg.add_input_text(
                                        tag="nRCmax", 
                                        default_value=EIS.parameter["KK"]["nRCmax"])
                                    dpg.add_checkbox(
                                        tag="KK_test",
                                        label="KK_test",
                                        default_value= True,
                                        callback=lambda sender, app_data: KK_test_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("No. RC")
                                    dpg.add_input_text(
                                        tag="nRC", 
                                        default_value=EIS.parameter["KK"]["nRC"])
                                    dpg.add_checkbox(
                                        tag="KK_type",
                                        label="Mu criterion",
                                        default_value= False if EIS.parameter["KK"]["KK_type"] == "standard" else True,
                                        callback=lambda sender, app_data: KK_type_callback(sender, app_data, EIS))
                                with dpg.table_row():
                                    dpg.add_text("MU threshold")
                                    dpg.add_input_text(
                                        tag="mu_threshold", 
                                        default_value=EIS.parameter["KK"]["mu_threshold"])

                                # EIS Preprocessing Parameters
                                with dpg.table_row():
                                    dpg.add_text("Smooth PPD")
                                    dpg.add_input_text(tag="Smooth_PointsPerDecade", default_value=EIS.parameter["Smoothing"]["PointsPerDecade"])
                                with dpg.table_row():
                                    dpg.add_text("Ex. fmin [Hz]")
                                    dpg.add_input_text(tag="extrapolation_fmin", default_value=EIS.parameter["Extrapolation"]["fmin"])
                                with dpg.table_row():
                                    dpg.add_text("Ex. fmax [Hz]")
                                    dpg.add_input_text(tag="extrapolation_fmax", default_value=f"{EIS.parameter['Extrapolation']['fmax']:.0e}")
                                with dpg.table_row():
                                    dpg.add_text("Extrap. PPD")
                                    dpg.add_input_text(tag="Extrapolation_PointsPerDecade", default_value=EIS.parameter["Extrapolation"]["PointsPerDecade"])    

                        # Z-HIT parameters
                        with dpg.tab(label="ZHIT", tag="tab_eis_parameter_ZHIT"):
                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))

                                with dpg.table_row():
                                    dpg.add_text("Enable ZHIT")
                                    dpg.add_checkbox(
                                        tag="zhit_enable",
                                        default_value=EIS.parameter["ZHIT"]["enable"]
                                    )
                                    dpg.add_text("Z-HIT modulus validation")
                                with dpg.table_row():
                                    dpg.add_text("Poly order")
                                    dpg.add_input_text(
                                        tag="zhit_poly_order",
                                        default_value=EIS.parameter["ZHIT"]["poly_order"]
                                    )
                                    dpg.add_text("Savitzky-Golay order")
                                with dpg.table_row():
                                    dpg.add_text("Window fraction")
                                    dpg.add_input_text(
                                        tag="zhit_window_frac",
                                        default_value=EIS.parameter["ZHIT"]["window_frac"]
                                    )
                                    dpg.add_text("0-1 relative SG window")
                        
                        # Manual Point Removal parameters
                        with dpg.tab(label="Manual Removal", tag="tab_eis_parameter_manual"):

                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):

                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))

                                # Enable checkbox (NO popup here)
                                with dpg.table_row():
                                    dpg.add_text("Enable removal")
                                    dpg.add_checkbox(
                                        tag="checkbox_manual_remove_batch_points",
                                        default_value=EIS.parameter["ManualRemoval"]["enable"],
                                        callback=lambda sender, app_data: manual_removal_callback(sender, app_data, config, EIS)
                                    )
                                    dpg.add_text("")

                                # Indices input
                                with dpg.table_row():
                                    dpg.add_text("Indices (1-based)")
                                    dpg.add_input_text(
                                        tag="input_manual_remove_batch_indices",
                                        hint="Example: 2,3,5-10",
                                        enabled=dpg.get_value("checkbox_manual_remove_batch_points"),
                                        default_value=gui_utils.eis_batch_manual.compress_indices([i+1 for i in EIS.parameter["ManualRemoval"]["indices"]]),
                                        width=-1
                                    )
                                    dpg.add_text("")

                                # THIS IS WHERE YOU PUT IT
                                with dpg.table_row():
                                    dpg.add_text("Interactive selector")
                                    dpg.add_button(
                                        tag = "button_manual_cut_batch",
                                        label="Open selector",
                                        enabled=dpg.get_value("checkbox_manual_remove_batch_points"),
                                        callback=lambda s, a: gui_utils.eis_batch_manual.open_manual_cut_window(config)
                                    )
                                    dpg.add_text("")

                                # Reset button
                                with dpg.table_row():
                                    dpg.add_text("Reset")
                                    dpg.add_button(
                                        tag = "button_manual_cut_batch_reset",
                                        label="Clear",
                                        enabled=dpg.get_value("checkbox_manual_remove_batch_points"),
                                        callback=lambda s, a: gui_utils.eis_batch_manual.reset_batch_cut(config)
                                    )
                                    dpg.add_text("")

                # Window for the buttons
                with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.082), horizontal_scrollbar=True, menubar=False, tag="child_window_eis_buttons"):
                    with dpg.group(horizontal=True):
                        dpg.add_button(tag="Button_data_import", label="Data import", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.eis_functions.data_import(s, a, config, EIS))
                        dpg.bind_item_theme("Button_data_import", blue_button_theme)

                        dpg.add_button(tag="Button_drt_Process_dataters", label="Load parameters", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.eis_functions.load_parameters(s, a, config, EIS))
                        dpg.bind_item_theme("Button_drt_Process_dataters", blue_button_theme)

                        dpg.add_button(tag="Button_Process_data", label="Process data", width=int(viewport_width*0.075), callback=lambda s, a: callback_process_data(s, a, EIS, config))
                        dpg.bind_item_theme("Button_Process_data", blue_button_theme)

                        dpg.add_button(tag="Button_Save_EIS", label="Save EIS", width=-1, callback=lambda s, a: gui_utils.eis_functions.save_eis(s, a, config, EIS))
                        dpg.bind_item_theme("Button_Save_EIS", blue_button_theme)
                        
                    with dpg.group(horizontal=True, tag="group_eis_display_file"):
                        dpg.add_text("Displayed file:")
                        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_eis_plot_file", "group_eis_display_file")
                
                # Window for the data display
                with dpg.child_window(width=int(viewport_width*0.33), height=-1, horizontal_scrollbar=True, menubar=False, border=False, tag="child_window_eis_data"):
                    with dpg.tab_bar(tag="tab_bar_eis_data"):
                        gui_utils.eis_table.table_update(config)

            # Window for the plot display
            with dpg.child_window(width=-1, height=-1, horizontal_scrollbar=False, menubar=False, border=True, tag="child_window_eis_plot"):
                with dpg.tab_bar(tag="tab_bar_eis_plot"):
                    with dpg.tab(label="Single", tag="tab_eis_plot_single"):
                        with dpg.tab_bar(tag="tab_bar_eis_plot_single"):
                            gui_utils.eis_plots.update_single_plots(config)
                    with dpg.tab(label="All", tag="tab_eis_plot_all"):
                        with dpg.tab_bar(tag="tab_bar_eis_plot_all"):
                            gui_utils.eis_plots.update_all_plots(config)
    # Update the child window size when the viewport is resized
    gui_utils.file_list.display_file(
        None,
        config.display_file,
        config,
        refresh_eis_tab=True,
        refresh_drt_tab=False,
        refresh_cnls_tab=False,
    )
    dpg.set_value("tab_bar_main", 'tab_eis')
    update_child_window_size()

                            