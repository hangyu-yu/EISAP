import os
import dearpygui.dearpygui as dpg
import glob
import numpy as np
import pandas as pd
import src.GUI.Utils as gui_utils

# Callback function to handle the options
def update_child_window_size():
    """
    Update the size of the child window based on the viewport size.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the width and height of the child window
    dpg.configure_item("child_window_file_list_drt", width=int(viewport_width * 0.33), height=int(viewport_height * 0.2))
    dpg.configure_item("child_window_parameter_drt", width=int(viewport_width * 0.33), height=int(viewport_height * 0.285))
    dpg.configure_item("child_window_drt_buttons", width=int(viewport_width * 0.33), height=int(viewport_height * 0.082))
    dpg.configure_item("child_window_drt_data", width=int(viewport_width * 0.33), height=-1)
    dpg.configure_item("child_window_drt_plot", width=-1, height=-1)
    dpg.configure_item("Button_calculate_lambdaopt", width=int(viewport_width*0.075))
    dpg.configure_item("Button_drt_load_parameters", width=int(viewport_width*0.075))
    dpg.configure_item("Button_drt_Process_data", width=int(viewport_width*0.075))
    dpg.configure_item("Button_Save_DRT", width=-1)

def lambda_mode_callback(sender, app_data, EIS):
    """
    Callback function for the lambda mode checkbox.
    """
    if app_data:
        mode = 'Optimal'
        dpg.configure_item("input_text_lambda", enabled=True, default_value='Optima')
    else:
        mode = 'Manual'
        dpg.configure_item("input_text_lambda", enabled=False, default_value=EIS.parameter["DRT"]["lambda"])
    EIS.parameter["DRT"]["Lambda_selection"] = mode
    print(f"Lambda mode set to {mode}")

def lambda_opt_callback(sender, app_data, EIS):
    """
    Callback function for the lambda optimal checkbox.
    """
    if app_data:
        EIS.parameter["LambdaOpt"]["lampda_opt"] = True
    else:
        EIS.parameter["LambdaOpt"]["lampda_opt"] = False
    print(f"Lambda optimal set to {app_data}")

def callback_process_data(sender, app_data, config):
    """
    Callback function to process and update EIS data in the GUI.
    """
    gui_utils.drt_functions.process_data(sender, app_data, config)
    gui_utils.drt_table.table_update(config)
    gui_utils.drt_plots.update_single_plots(config)
    gui_utils.drt_plots.update_all_plots(config)

# Main tab function for EIS
def gui_tab_drt(config, EIS, CNLS):
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the theme for different widgets
    with dpg.theme() as blue_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135, 255))  # Background color (blue)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))  # Text color (white)

    with dpg.tab(label="DRT", tag="tab_drt"):
        with dpg.group(horizontal=True):
            with dpg.group():
                # Window for file list
                with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.2), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_drt"):
                    gui_utils.file_list.update_file_list(config, "child_window_file_list_drt", EIS, CNLS)

                # Window for the parameters
                with dpg.child_window(width=int(viewport_width * 0.33), height=int(viewport_height * 0.285), horizontal_scrollbar=True, menubar=True, tag="child_window_parameter_drt"):
                    with dpg.menu_bar(parent="child_window_parameter_drt"):
                        with dpg.menu(label="Parameters"):
                            dpg.add_menu_item(label="")
                    with dpg.table(
                        header_row=False,
                        borders_innerH=False,
                        row_background=False,
                        policy=dpg.mvTable_SizingStretchSame
                    ):
                        # Two columns for the sample name and the sample type
                        dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//6))
                        dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                        dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width//12))
                        
                        # Table content
                        with dpg.table_row():
                            dpg.add_checkbox(
                                tag="check_box_lambda_mode",
                                label="Optimal lambda",
                                default_value=False,
                                callback=lambda sender, app_data: lambda_mode_callback(sender, app_data, EIS))
                            dpg.add_text("Lambda:", tag="text_lambda")
                            dpg.add_input_text(tag="input_text_lambda", default_value=EIS.parameter["DRT"]["lambda"], enabled=True)
                        with dpg.table_row():
                            dpg.add_text("")
                        with dpg.table_row():
                            dpg.add_text("Optimal lambda parameters:")
                            dpg.add_text("Min. lambda:", tag="text_min_lambda")
                            dpg.add_input_text(tag="input_text_min_lambda", default_value=EIS.parameter["LambdaOpt"]["lambda_min"], enabled=True)
                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Max. lambda:", tag="text_max_lambda")
                            dpg.add_input_text(tag="input_text_max_lambda", default_value=EIS.parameter["LambdaOpt"]["lambda_max"], enabled=True)
                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Lambda points:", tag="text_lambda_points")
                            dpg.add_input_text(tag="input_text_lambda_points", default_value=EIS.parameter["LambdaOpt"]["n"], enabled=True)
                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Optimal lambda:")
                            dpg.add_text("Non-calculated", tag="text_optimal_lambda")
                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Average lambda:")
                            dpg.add_text("Non-calculated", tag="text_average_lambda")

                # Window for the buttons
                with dpg.child_window(width=int(viewport_width*0.33), height=int(viewport_height*0.082), horizontal_scrollbar=True, menubar=False, tag="child_window_drt_buttons"):
                    with dpg.group(horizontal=True):
                        dpg.add_button(tag="Button_drt_load_parameters", label="Load parameters", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.drt_functions.load_parameters(s, a, config))
                        dpg.bind_item_theme("Button_drt_load_parameters", blue_button_theme)

                        dpg.add_button(tag="Button_calculate_lambdaopt", label="Compute lambda", width=int(viewport_width*0.075), callback=lambda s, a: gui_utils.drt_functions.lambdaopt(s, a, config))
                        dpg.bind_item_theme("Button_calculate_lambdaopt", blue_button_theme)

                        dpg.add_button(tag="Button_drt_Process_data", label="Process data", width=int(viewport_width*0.075), callback=lambda s, a: callback_process_data(s, a, config))
                        dpg.bind_item_theme("Button_drt_Process_data", blue_button_theme)

                        dpg.add_button(tag="Button_Save_DRT", label="Save DRT", width=-1, callback=lambda s, a: gui_utils.drt_functions.save_drt(s, a, config))
                        dpg.bind_item_theme("Button_Save_DRT", blue_button_theme)
                    
                    if config.display_file is None or config.display_file == "":
                        config.display_file = config.selected_files[0] if config.selected_files else None

                    with dpg.group(horizontal=True):
                        dpg.add_text("Displayed file:")
                        dpg.add_combo(
                            tag="combo_drt_plot_file",
                            default_value = config.display_file,
                            width = -1,
                            items = config.selected_files,
                            callback=lambda s, a: gui_utils.file_list.display_file(s, a, config)
                    )
                
                # Window for the data display
                with dpg.child_window(width=int(viewport_width*0.33), height=-1, horizontal_scrollbar=True, menubar=False, border=False, tag="child_window_drt_data"):
                    with dpg.tab_bar(tag="tab_bar_drt_data"):
                        gui_utils.drt_table.table_update(config)

            # Window for the plot display
            with dpg.child_window(width=-1, height=-1, horizontal_scrollbar=True, menubar=False, border=True, tag="child_window_drt_plot"):
                with dpg.tab_bar(tag="tab_bar_drt_plot"):
                    with dpg.tab(label="Single", tag="tab_drt_plot_single"):
                        with dpg.tab_bar(tag="tab_bar_drt_plot_single"):
                            gui_utils.drt_plots.update_single_plots(config)
                    with dpg.tab(label="All", tag="tab_drt_plot_all"):
                        with dpg.tab_bar(tag="tab_bar_drt_plot_all"):
                            gui_utils.drt_plots.update_all_plots(config)
                            
    # Update the child window size when the viewport is resized
    dpg.set_viewport_resize_callback(update_child_window_size)
                            