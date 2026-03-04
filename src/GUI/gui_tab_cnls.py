import os
import copy
import numpy as np
import pandas as pd
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg

# Callback function to handle the options
def update_child_window_size():
    """
    Update the size of the child window based on the viewport size.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Set the width and height of the child window
    dpg.configure_item("child_window_file_list_cnls", width=int(viewport_width * 0.45), height=int(viewport_height * 0.15))
    dpg.configure_item("child_window_parameter_cnls", width=int(viewport_width * 0.45), height=int(viewport_height * 0.35))
    dpg.configure_item("child_window_cnls_buttons", width=int(viewport_width * 0.45), height=int(viewport_height * 0.082))
    dpg.configure_item("child_window_cnls_data", width=int(viewport_width * 0.45), height=-1)
    dpg.configure_item("child_window_cnls_elements", width=int(viewport_width * 0.3), height=-1)
    dpg.configure_item("child_window_cnls_plot", width=-1, height=-1)
    dpg.configure_item("child_window_cnls_parameters", width=-1, height=-1)
    dpg.configure_item("Button_cnls_cnls_fit", width=int(viewport_width*0.1))
    dpg.configure_item("Button_cnls_load_parameters", width=int(viewport_width*0.1))
    dpg.configure_item("Button_cnls_initialize_parameters", width=int(viewport_width*0.1))
    dpg.configure_item("Button_Save_CNLS", width=-1)

def _initialization_cnls(config, CNLS):
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS/DRT processing is not done.')
        elif 'CNLS' not in config.store[file_name_no_ext].keys():
            config.store[file_name_no_ext]['CNLS'] = copy.deepcopy(CNLS)
            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            CNLS_tmp.file_folder = config.folder_path
            CNLS_tmp.filename = os.path.basename(file_name)
            print(f"---- CNLS data initialized from {file_name} successfully.")

# Main tab function for EIS
def gui_tab_cnls(config, EIS, CNLS):
    config.save_config()
    dpg.delete_item("tab_cnls", children_only=False)  # Clear the tab content if it exists
    # Initialize the configuration
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    _initialization_cnls(config, CNLS)

    # Set the theme for different widgets
    with dpg.theme() as blue_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135, 255))  # Background color (blue)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))  # Text color (white)

    with dpg.tab(label="CNLS", tag="tab_cnls", parent="tab_bar_main"):
        with dpg.group(horizontal=True):
            with dpg.group():
                # Window for file list
                with dpg.child_window(width=int(viewport_width * 0.45), height=int(viewport_height*0.15), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_cnls"):
                    gui_utils.file_list.update_file_list(config, "child_window_file_list_cnls", EIS, CNLS)

                # Window for the parameters
                with dpg.child_window(width=int(viewport_width * 0.45), height=int(viewport_height * 0.35), horizontal_scrollbar=True, menubar=True, tag="child_window_parameter_cnls"):
                    with dpg.menu_bar(parent="child_window_parameter_cnls", tag="menu_cnls_parameters"):
                        with dpg.menu(label="Parameters"):
                            dpg.add_checkbox(
                                label="Fix all plots",
                                callback=lambda s, a: setattr(config, 'fix_all_plots_CNLS', a),
                            )
                        with dpg.menu(label="Add elements"):
                            for header, element in config.store['element_list'].items():
                                dpg.add_menu_item(
                                    label=f"Add {header}",
                                    callback=lambda s, a: gui_utils.cnls_elements.add_element(s, a, config)
                                )
                        gui_utils.cnls_elements.menu_remove_elements(config)
                    
                    # CNLS elements and parameter tables
                    with dpg.group(horizontal=True):
                        with dpg.child_window(width=int(viewport_width*0.3), height=-1, horizontal_scrollbar=True, menubar=False, no_scrollbar= False, tag="child_window_cnls_elements", border=False):
                            gui_utils.cnls_elements.update_elements(config)

                        # Window for the CNLS parameters
                        with dpg.child_window(width=-1, height=-1, border=False, horizontal_scrollbar=True, menubar=False, tag="child_window_cnls_parameters"):
                            dpg.add_checkbox(
                                tag="checkbox_cnls_segement_constraints",
                                label="Segment constraints",
                                default_value = True if config.store['segment_constraints'] == 'segment' else False,
                                callback=lambda s, a: gui_utils.cnls_functions.segment_constraints(s, a, config)
                            )

                            with dpg.table(
                                tag = "Table_cnls_parameters",
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                borders_outerH=False,
                                policy=dpg.mvTable_SizingStretchSame
                            ):
                                # Two columns for the sample name and the sample type
                                dpg.add_table_column(tag="cnls_parameter_column1", width_stretch=True)
                                dpg.add_table_column(tag="cnls_parameter_column2", width_stretch=True)

                                # Table contents
                                with dpg.table_row():
                                    dpg.add_checkbox(
                                    tag="checkbox_cnls_R_percentage",
                                    label="R Cons %",
                                    default_value = False
                                    )
                                    dpg.add_input_float(
                                        tag=f"input_constraints_R_percentage",
                                        format="%.1f",
                                        enabled=True if config.store['segment_constraints'] == 'segment' else False,
                                        default_value=10,
                                        width=-1,
                                        step=0,
                                        step_fast=0,
                                        min_value=1e-100,
                                        max_value=1e100,
                                    )
                                with dpg.table_row():
                                    dpg.add_checkbox(
                                    tag="checkbox_cnls_Tau_percentage",
                                    label="Tau Cons %",
                                    default_value = False
                                    )
                                    dpg.add_input_float(
                                        tag=f"input_constraints_Tau_percentage",
                                        format="%.1f",
                                        enabled=True if config.store['segment_constraints'] == 'segment' else False,
                                        default_value=10,
                                        width=-1,
                                        step=0,
                                        step_fast=0,
                                        min_value=1e-100,
                                        max_value=1e100,
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Data_type:")
                                    dpg.add_combo(
                                        tag="combo_cnls_data_type",
                                        default_value = CNLS.data_type,
                                        width = -1,
                                        items = ["truncated", "smooth_KK", "smooth_DRT", "extrapolation", "LCcorrect"],
                                        callback=lambda s, a: gui_utils.cnls_functions.update_data_type(s, a, config)
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Peak ID:")
                                    dpg.add_combo(
                                        tag="combo_peak_ID",
                                        default_value = 'fixed',
                                        width = -1,
                                        items = ["fixed", "manual", "auto"],
                                        callback=lambda s, a: gui_utils.cnls_functions.peak_mode(s, a, config)
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Nbr iters:")
                                    dpg.add_input_int(
                                        tag="input_nbr_iters",
                                        default_value = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].iteration if gui_utils.cnls_functions._file_existence_check(config) and config.store[os.path.splitext(config.display_file)[0]]['CNLS'].iteration is not None else 5,
                                        width = -1,
                                        min_value = 1,
                                        max_value = 10,
                                        callback=lambda s, a: gui_utils.cnls_functions.nbr_iteration(s, a, config)
                                    )
                                with dpg.table_row():
                                    dpg.add_text("Nbr peaks:")
                                    dpg.add_input_int(
                                        tag="input_nbr_peaks",
                                        default_value = len(config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_fixed) if gui_utils.cnls_functions._file_existence_check(config) and config.store[os.path.splitext(config.display_file)[0]]['CNLS'].f_fixed is not None else 5,
                                        width = -1,
                                        min_value = 1,
                                        max_value = 10000,
                                        callback=lambda s, a: gui_utils.cnls_functions.dynamic_peak_ids(s, a, config)
                                    )
                                gui_utils.cnls_functions.dynamic_peak_ids(0, 0, config)

                # Window for the buttons
                with dpg.child_window(width=int(viewport_width * 0.45), height=int(viewport_height*0.082), horizontal_scrollbar=True, menubar=False, tag="child_window_cnls_buttons"):
                    with dpg.group(horizontal=True):
                        dpg.add_button(tag="Button_cnls_initialize_parameters", label="Initialize param.", width=int(viewport_width*0.1), callback=lambda s, a: gui_utils.cnls_functions.initialize_parameters(s, a, config))
                        dpg.bind_item_theme("Button_cnls_initialize_parameters", blue_button_theme)

                        dpg.add_button(tag="Button_cnls_load_parameters", label="Load parameters", width=int(viewport_width*0.1), callback=lambda s, a: gui_utils.cnls_functions.load_parameters(s, a, config))
                        dpg.bind_item_theme("Button_cnls_load_parameters", blue_button_theme)

                        dpg.add_button(tag="Button_cnls_cnls_fit", label="CNLS fit", width=int(viewport_width*0.1), callback=lambda s, a: gui_utils.cnls_functions.cnls_fit(s, a, config))
                        dpg.bind_item_theme("Button_cnls_cnls_fit", blue_button_theme)

                        dpg.add_button(tag="Button_Save_CNLS", label="Save CNLS", width=-1, callback=lambda s, a: gui_utils.cnls_functions.save_cnls(s, a, config, CNLS))
                        dpg.bind_item_theme("Button_Save_CNLS", blue_button_theme)

                    with dpg.group(horizontal=True, tag="group_cnls_display_file"):
                        dpg.add_text("Displayed file:")
                        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_display_file_cnls", "group_cnls_display_file")
                
                # Window for the data display
                with dpg.child_window(width=int(viewport_width * 0.45), height=-1, horizontal_scrollbar=True, menubar=False, border=False, tag="child_window_cnls_data"):
                    with dpg.tab_bar(tag="tab_bar_cnls_data"):
                        gui_utils.cnls_table.table_update(config)

            # Window for the plot display
            with dpg.group():
                with dpg.child_window(width=-1, height=-1, horizontal_scrollbar=True, menubar=False, border=True, tag="child_window_cnls_plot"):
                    pass
                    with dpg.tab_bar(tag="tab_bar_cnls_plot"):
                        with dpg.tab(label="Single", tag="tab_cnls_plot_single"):
                            with dpg.tab_bar(tag="tab_bar_cnls_plot_single"):
                                gui_utils.cnls_plots.update_single_plots(config)
                        with dpg.tab(label="All", tag="tab_cnls_plot_all"):
                            with dpg.tab_bar(tag="tab_bar_cnls_plot_all"):
                                gui_utils.cnls_plots.update_all_plots(config)
                            
    # Update the child window size when the viewport is resized
    gui_utils.file_list.display_file(None, config.display_file, config)
    dpg.set_value("tab_bar_main", 'tab_cnls')
    dpg.set_viewport_resize_callback(update_child_window_size)
                            