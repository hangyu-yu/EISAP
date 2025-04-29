import os
import dearpygui.dearpygui as dpg
import glob
import numpy as np
import pandas as pd
import src.GUI.Utils as gui_utils

# Callback function to handle the options
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

def display_file(sender, app_data, config):
    """
    Callback function to display the selected file in the combo box.
    """
    # Update the displayed file name in the GUI
    config.display_file = dpg.get_value(sender)
    
    # Print the selected file for debugging
    print(f"---- File to plot: {config.display_file}")

# Main tab function for EIS
def gui_tab_eis(config, EIS, CNLS):
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the theme for different widgets
    with dpg.theme() as blue_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135, 255))  # Background color (blue)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))  # Text color (white)
            
    with dpg.theme() as table_theme:
        # Header style (underline + background color)
        with dpg.theme_component(dpg.mvTable):
            # Header underline
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 5, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (70, 70, 70))  # Header background color
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (100, 100, 100))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (50, 50, 50))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))  # Header text color

        # Alternating row colors
        with dpg.theme_component(dpg.mvTableRow):
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (40, 40, 40))         # Odd rows
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (60, 60, 60))      # Even rows
        
        # Center-align text in table cells
        with dpg.theme_component(dpg.mvTable):
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 10, 10)  # Adjust padding for centering
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)    # Remove extra spacing
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)   # Adjust frame padding

    with dpg.tab(label="EIS", tag="tab_eis"):
        # Window for file list
        with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.2), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_eis"):
            gui_utils.file_list.update_file_list(config, "child_window_file_list_eis", EIS, CNLS)
            # Monitor function to be updated
            # gui_utils.file_monitor.bind_tab_switch_update(
            #     tab_tag="tab_eis",
            #     config=config,
            #     update_callback=lambda: gui_utils.file_list.update_file_list(
            #         config, "child_window_file_list_eis"
            #     )
            # )

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
                                callback=lambda sender, app_data: file_selector_ok_callback(sender, app_data, config),
                                tag="file_dialog_eis",
                                cancel_callback=lambda sender, app_data: file_selector_cancel_callback(sender, app_data),
                                width=700,
                                height=400):
                                dpg.add_file_extension(".py", color=(0, 255, 0, 255), custom_text="[Python]")
                            dpg.add_button(
                                label="Data import function",
                                callback=lambda: dpg.show_item("file_dialog_eis"),
                                tag="button_data_import_function"
                            )
                        with dpg.table_row():
                            dpg.add_text("Upper cut:", tag="text_num_cut_upper")
                            dpg.add_input_text(tag="num_cut_upper", default_value=EIS.parameter["Preprocessing"]["num_cut_upper"])
                            dpg.add_text(os.path.basename(config.data_import_function), tag="function_import")
                        with dpg.table_row():
                            dpg.add_text("Lower cut:", tag="text_num_cut_lower")
                            dpg.add_input_text(tag="num_cut_lower", default_value=EIS.parameter["Preprocessing"]["num_cut_lower"])
                        with dpg.table_row():
                            dpg.add_text("Min significance:", tag="text_sig_threshold")
                            dpg.add_input_text(tag="sig_threshold", default_value=EIS.parameter["RM_significance"]["sig_threshold"])
                            
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
                            dpg.add_text("Max. KK res.")
                            dpg.add_input_text(tag="kk_threshold", default_value=EIS.parameter["KK"]["kk_threshold"])
                            dpg.add_checkbox(
                                tag="RmNonKK",
                                label="Remove low KK data",
                                default_value= True,
                                callback=lambda sender, app_data: RmNonKK_callback(sender, app_data, EIS))
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

        # Window for the data import buttons
        with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.066), horizontal_scrollbar=True, menubar=False, tag="child_window_eis_buttons"):
            with dpg.group(horizontal=True):
                dpg.add_button(tag="Button_data_import", label="Data import", width=int(viewport_width*0.104), callback=lambda s, a: gui_utils.eis_functions.data_import(s, a, config, EIS))
                dpg.bind_item_theme("Button_data_import", blue_button_theme)

                dpg.add_button(tag="Button_load_parameters", label="Load parameters", width=int(viewport_width*0.104), callback=lambda s, a: gui_utils.eis_functions.load_parameters(s, a, config, EIS))
                dpg.bind_item_theme("Button_load_parameters", blue_button_theme)

                dpg.add_button(tag="Button_Process_data", label="Process data", width=-1, callback=lambda s, a: gui_utils.eis_functions.process_data(s, a, config, EIS))
                dpg.bind_item_theme("Button_Process_data", blue_button_theme)
            with dpg.group(horizontal=True):
                dpg.add_text("Displayed file:")
                dpg.add_combo(
                    tag="Combo_plot_file",
                    default_value = config.selected_files[0] if config.selected_files else None,
                    width = -1,
                    items = config.selected_files,
                    callback=lambda s, a: display_file(s, a, config)
            )
        
        # Window for the data display
        with dpg.child_window(width=int(viewport_width*0.33), height=-1, horizontal_scrollbar=True, menubar=False, tag="child_window_eis_data"):
            with dpg.tab_bar(tag="tab_bar_eis_data"):
                for idx, data_category in enumerate(["KK_data", "raw", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
                    with dpg.tab(label=data_category, tag=f"tab_eis_{data_category}_data"):
                        with dpg.table(
                            header_row=True,
                            borders_innerV=True,  # Show vertical column lines
                            borders_outerV=True,
                            borders_outerH=True,
                            row_background=True,  # Enable alternating row colors
                            reorderable=True,     # Allow column reordering via drag-and-drop
                            freeze_rows=1,        # Freeze header row (fixed during scrolling)
                            scrollX=True,         # Enable horizontal scrolling
                            scrollY=True,         # Enable vertical scrolling
                            policy=dpg.mvTable_SizingFixedFit  # Automatically adjust column width
                        ):
                            if data_category != "KK_data":
                                dpg.add_table_column(label="Index", width_fixed=True)
                                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                                dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Z [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Phase [deg]", width_stretch=True)
                            else:
                                dpg.add_table_column(label="Index", width_fixed=True)
                                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                                dpg.add_table_column(label="Re residual [%]", width_stretch=True)
                                dpg.add_table_column(label="Im residual [%]", width_stretch=True)
                        if data_category == "KK_data" and not config.display_file == []:
                            with dpg.group(horizontal=True):
                                dpg.add_text(f"Ohmic resistance [Ω·cm2]: {config.store[os.path.splitext(config.display_file)[0]]['EIS'].KK_data['res_ohm_kk']:.2f},")
                                dpg.add_text(f"Polarization resistance [Ω·cm2]: {config.store[os.path.splitext(config.display_file)[0]]['EIS'].KK_data['res_pol_kk']:.2f}")
                        dpg.bind_item_theme(f"tab_eis_{data_category}_data", table_theme)