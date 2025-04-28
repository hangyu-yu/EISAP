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

# Main tab function for EIS
def gui_tab_eis(config, EIS):
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    with dpg.tab(label="EIS", tag="tab_eis"):
        # Window for file list
        with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.33), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_eis"):
            gui_utils.file_list.update_file_list(config, "child_window_file_list_eis")
            # Monitor function to be updated
            # gui_utils.file_monitor.bind_tab_switch_update(
            #     tab_tag="tab_eis",
            #     config=config,
            #     update_callback=lambda: gui_utils.file_list.update_file_list(
            #         config, "child_window_file_list_eis"
            #     )
            # )

        # Window for the parameters
        with dpg.child_window(
            width=int(viewport_width * 0.33),
            height=int(viewport_height * 0.285),
            horizontal_scrollbar=True,
            menubar=True,
            tag="child_window_parameter_eis"
        ):
            with dpg.menu_bar(parent="child_window_parameter_eis"):
                with dpg.menu(label="Parameters"):
                    dpg.add_menu_item(label="")
            with dpg.tab_bar(tag="tab_bar_eis_parameters"):
                # Sample parameters
                with dpg.tab(label="General", tag="tab_eis_parameter_sample"):
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
                            dpg.add_text("Cell area [cm²]:")
                            dpg.add_input_text(tag="CellArea", default_value=EIS.parameter["Sample"]["CellArea"])
                            dpg.add_checkbox(
                                tag="rm_significance",
                                label="Remove low sig. data",
                                callback=lambda sender, app_data: rm_significance_callback(sender, app_data, EIS))
                        with dpg.table_row():
                            dpg.add_text("Cell No.:")
                            dpg.add_input_text(tag="n_cell", default_value=EIS.parameter["Sample"]["n_cell"])
                            dpg.add_checkbox(
                                tag="rm_outliers",
                                label="Remove outliers",
                                default_value=EIS.parameter["Rmoutliers"]["Rmoutliers"],
                                callback=lambda sender, app_data: rm_outliers_callback(sender, app_data, EIS))
                        with dpg.table_row():
                            dpg.add_text("Instrument")
                            dpg.add_input_text(tag="instrument_type", default_value=EIS.parameter["Sample"]["instrument_type"])
                        with dpg.table_row():
                            dpg.add_text("Upper cut:")
                            dpg.add_input_text(tag="num_cut_upper", default_value=EIS.parameter["Preprocessing"]["num_cut_upper"])
                        with dpg.table_row():
                            dpg.add_text("Lower cut:")
                            dpg.add_input_text(tag="num_cut_lower", default_value=EIS.parameter["Preprocessing"]["num_cut_lower"])
                        with dpg.table_row():
                            dpg.add_text("Min significance:")
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
                            dpg.add_input_text(                               tag="extrapolation_fmax", default_value=f"{EIS.parameter['Extrapolation']['fmax']:.0e}"
                            )
                        with dpg.table_row():
                            dpg.add_text("Extrap. PPD")
                            dpg.add_input_text(tag="Extrapolation_PointsPerDecade", default_value=EIS.parameter["Extrapolation"]["PointsPerDecade"])
