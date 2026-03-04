import os
import glob
import numpy as np
import pandas as pd
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg


def update_child_window_size():
    """
    Update the size of the child window based on the viewport size.
    Safe-guards added to avoid configure_item on missing tags.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    def safe_configure(tag, **kwargs):
        if dpg.does_item_exist(tag):
            dpg.configure_item(tag, **kwargs)

    safe_configure("child_window_file_list_drt", width=int(viewport_width * 0.33), height=int(viewport_height * 0.2))
    safe_configure("child_window_parameter_drt", width=int(viewport_width * 0.33), height=int(viewport_height * 0.285))
    safe_configure("child_window_drt_buttons", width=int(viewport_width * 0.33), height=int(viewport_height * 0.082))
    safe_configure("child_window_drt_data", width=int(viewport_width * 0.33), height=-1)
    safe_configure("child_window_drt_plot", width=-1, height=-1)

    safe_configure("Button_calculate_lambdaopt", width=int(viewport_width * 0.075))
    safe_configure("Button_drt_load_parameters", width=int(viewport_width * 0.075))
    safe_configure("Button_drt_Process_data", width=int(viewport_width * 0.075))
    safe_configure("Button_Save_DRT", width=-1)


def lambda_mode_callback(sender, app_data, EIS, config):
    """
    Callback function for the lambda mode checkbox.
    """
    mode = "Manual"
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError("The specified file is not loaded or EIS processing is not done.")
        else:
            EIS_tmp = config.store[file_name_no_ext]["EIS"]
            if app_data:
                mode = "Optimal"
                if dpg.does_item_exist("input_text_lambda"):
                    dpg.configure_item("input_text_lambda", enabled=False)
                    dpg.set_value("input_text_lambda", "Optimal")
            else:
                mode = "Manual"
                file_name_no_ext_dis = os.path.splitext(config.display_file)[0]
                if dpg.does_item_exist("input_text_lambda"):
                    dpg.configure_item("input_text_lambda", enabled=True)
                    dpg.set_value(
                        "input_text_lambda",
                        config.store[file_name_no_ext_dis]["EIS"].parameter["DRT"]["lambda"],
                    )
            EIS_tmp.parameter["DRT"]["Lambda_selection"] = mode

    print(f"-- Lambda mode set to {mode}")


def tknv_pos_callback(sender, app_data, EIS, config):
    """
    Callback function for the tikhonov positive checkbox.
    """
    mode = False
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError("The specified file is not loaded or EIS processing is not done.")
        else:
            EIS_tmp = config.store[file_name_no_ext]["EIS"]
            if app_data:
                mode = True
                if dpg.does_item_exist("input_text_lambda"):
                    dpg.configure_item("input_text_lambda", default_value=0.05, enabled=True)
                    dpg.set_value("input_text_lambda", 0.05)
                dpg.configure_item("check_box_lambda_mode", enabled=False)
                dpg.set_value("check_box_lambda_mode", False)
                dpg.configure_item("input_text_max_lambda", enabled=False, default_value="not available")
                dpg.configure_item("input_text_min_lambda", enabled=False, default_value="not available")
                dpg.configure_item("input_text_lambda_points", enabled=False, default_value="not available")
            else:
                mode = False
                file_name_no_ext_dis = os.path.splitext(config.display_file)[0]
                if dpg.does_item_exist("input_text_lambda"):
                    dpg.configure_item("input_text_lambda", default_value=0.0005, enabled=True)
                    dpg.set_value(
                        "input_text_lambda",
                        0.0005,
                    )
                dpg.configure_item("check_box_lambda_mode", enabled=True)
                dpg.set_value("check_box_lambda_mode", False)
                dpg.configure_item("input_text_max_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_max"])
                dpg.configure_item("input_text_min_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_min"])
                dpg.configure_item("input_text_lambda_points", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["n"])
            EIS_tmp.parameter["DRT"]["tknv_pos"] = mode

    print(f"-- Tikhonov positive mode set to {mode}")


def lambda_opt_callback(sender, app_data, EIS):
    """
    Callback function for the lambda optimal checkbox.
    """
    EIS.parameter["LambdaOpt"]["lampda_opt"] = bool(app_data)
    print(f"Lambda optimal set to {app_data}")


def _ensure_plot_tab_bars_exist():
    """
    The crash you saw happens when update_all_plots tries to add tabs but the parent tab_bar
    doesn't exist (or was deleted). This function guarantees the required containers exist.
    """
    # If the whole DRT tab was removed, nothing to do.
    if not dpg.does_item_exist("tab_drt"):
        return False

    # Ensure plot area exists
    if not dpg.does_item_exist("child_window_drt_plot"):
        return False

    # Ensure tab bar hierarchy exists. If your layout always creates these, this is just a safety net.
    if not dpg.does_item_exist("tab_bar_drt_plot"):
        with dpg.child_window(parent="tab_drt", tag="child_window_drt_plot", width=-1, height=-1):
            with dpg.tab_bar(tag="tab_bar_drt_plot"):
                pass

    # Ensure "All" tab and its internal tab_bar exist
    if not dpg.does_item_exist("tab_drt_plot_all"):
        with dpg.tab(parent="tab_bar_drt_plot", label="All", tag="tab_drt_plot_all"):
            with dpg.tab_bar(tag="tab_bar_drt_plot_all"):
                pass

    if not dpg.does_item_exist("tab_bar_drt_plot_all"):
        # tab exists but the internal tab_bar got deleted (or never created)
        with dpg.tab(parent="tab_bar_drt_plot", label="All", tag="tab_drt_plot_all"):
            with dpg.tab_bar(tag="tab_bar_drt_plot_all"):
                pass

    return True


def callback_process_data(sender, app_data, config):
    """
    Callback function to process and update EIS data in the GUI.

    Key fix: before calling update_all_plots, we guarantee tab_bar_drt_plot_all exists
    and we clear its children so update_all_plots can safely re-add tabs every time.
    """
    gui_utils.drt_functions.process_data(sender, app_data, config)
    gui_utils.drt_table.table_update(config)
    gui_utils.drt_plots.update_single_plots(config)

    # ---- SAFETY FIX FOR YOUR ERROR ----
    if _ensure_plot_tab_bars_exist():
        # Clear existing dynamic tabs so update_all_plots can recreate them without collisions.
        # This also prevents "Parent could not be deduced" when previous UI got deleted/rebuilt.
        dpg.delete_item("tab_bar_drt_plot_all", children_only=True)
        gui_utils.drt_plots.update_all_plots(config)
    # -----------------------------------

def gui_tab_drt(config, EIS, CNLS):
    config.save_config()

    # Don’t delete a tag that may not exist.
    if dpg.does_item_exist("tab_drt"):
        dpg.delete_item("tab_drt", children_only=False)

    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    # Theme for different widgets
    with dpg.theme() as blue_button_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135, 255))  # blue background
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))  # white text

    with dpg.tab(label="DRT", tag="tab_drt", parent="tab_bar_main"):
        with dpg.group(horizontal=True):
            with dpg.group():
                # File list
                with dpg.child_window(
                    width=int(viewport_width * 0.33),
                    height=int(viewport_height * 0.2),
                    horizontal_scrollbar=True,
                    menubar=True,
                    tag="child_window_file_list_drt",
                ):
                    gui_utils.file_list.update_file_list(config, "child_window_file_list_drt", EIS, CNLS)

                # Parameters
                with dpg.child_window(
                    width=int(viewport_width * 0.33),
                    height=int(viewport_height * 0.285),
                    horizontal_scrollbar=True,
                    menubar=True,
                    tag="child_window_parameter_drt",
                ):
                    with dpg.menu_bar(parent="child_window_parameter_drt"):
                        with dpg.menu(label="Parameters"):
                            dpg.add_menu_item(label="")

                    with dpg.table(
                        header_row=False,
                        borders_innerH=False,
                        row_background=False,
                        policy=dpg.mvTable_SizingStretchSame,
                    ):
                        dpg.add_table_column(tag="drt_parameter_column1", width_fixed=True, init_width_or_weight=int(viewport_width // 7))
                        dpg.add_table_column(tag="drt_parameter_column2", width_stretch=True)
                        dpg.add_table_column(tag="drt_parameter_column3", width_stretch=True)

                        with dpg.table_row():
                            dpg.add_checkbox(
                                tag="check_box_lambda_mode",
                                label="Optimal lambda",
                                default_value=False,
                                callback=lambda sender, app_data: lambda_mode_callback(sender, app_data, EIS, config),
                            )
                            dpg.add_text("Lambda:", tag="text_lambda")
                            dpg.add_input_text(
                                tag="input_text_lambda",
                                default_value=EIS.parameter["DRT"]["lambda"],
                                enabled=True,
                                width=-1,
                            )

                        with dpg.table_row():
                            dpg.add_checkbox(
                                tag="check_box_tknv_pos",
                                label="Tikhonov positive",
                                default_value=EIS.parameter["DRT"]["tknv_pos"],
                                callback=lambda sender, app_data: tknv_pos_callback(sender, app_data, EIS, config),
                            )
                            dpg.add_text("Optimal lambda param.:")
                            dpg.add_text("")

                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Min. lambda:", tag="text_min_lambda")
                            dpg.add_input_text(
                                tag="input_text_min_lambda",
                                default_value=EIS.parameter["LambdaOpt"]["lambda_min"] if EIS.parameter["DRT"]["tknv_pos"] is not True else "not available",
                                enabled=True,
                                width=-1,
                            )

                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Max. lambda:", tag="text_max_lambda")
                            dpg.add_input_text(
                                tag="input_text_max_lambda",
                                default_value=EIS.parameter["LambdaOpt"]["lambda_max"] if EIS.parameter["DRT"]["tknv_pos"] is not True else "not available",
                                enabled=True,
                                width=-1,
                            )

                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Lambda points:", tag="text_lambda_points")
                            dpg.add_input_text(
                                tag="input_text_lambda_points",
                                default_value=EIS.parameter["LambdaOpt"]["n"] if EIS.parameter["DRT"]["tknv_pos"] is not True else "not available",
                                enabled=True,
                                width=-1,
                            )

                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Optimal lambda:")
                            dpg.add_text("Non-calculated", tag="text_optimal_lambda")

                        with dpg.table_row():
                            dpg.add_text("")
                            dpg.add_text("Average lambda:")
                            dpg.add_text("Non-calculated", tag="text_average_lambda")

                # Buttons
                with dpg.child_window(
                    width=int(viewport_width * 0.33),
                    height=int(viewport_height * 0.082),
                    horizontal_scrollbar=True,
                    menubar=False,
                    tag="child_window_drt_buttons",
                ):
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            tag="Button_calculate_lambdaopt",
                            label="Compute lambda",
                            width=int(viewport_width * 0.075),
                            callback=lambda s, a: gui_utils.drt_functions.lambdaopt(s, a, config),
                        )
                        dpg.bind_item_theme("Button_calculate_lambdaopt", blue_button_theme)

                        dpg.add_button(
                            tag="Button_drt_load_parameters",
                            label="Load parameters",
                            width=int(viewport_width * 0.075),
                            callback=lambda s, a: gui_utils.drt_functions.load_parameters(s, a, config),
                        )
                        dpg.bind_item_theme("Button_drt_load_parameters", blue_button_theme)

                        dpg.add_button(
                            tag="Button_drt_Process_data",
                            label="Process data",
                            width=int(viewport_width * 0.075),
                            callback=lambda s, a: callback_process_data(s, a, config),
                        )
                        dpg.bind_item_theme("Button_drt_Process_data", blue_button_theme)

                        dpg.add_button(
                            tag="Button_Save_DRT",
                            label="Save DRT",
                            width=-1,
                            callback=lambda s, a: gui_utils.drt_functions.save_drt(s, a, config),
                        )
                        dpg.bind_item_theme("Button_Save_DRT", blue_button_theme)

                    with dpg.group(horizontal=True, tag="group_drt_display_file"):
                        dpg.add_text("Displayed file:")
                        gui_utils.file_list.update_file_list_and_display(0, 0, config, "combo_drt_plot_file", "group_drt_display_file")

                # Data display
                with dpg.child_window(
                    width=int(viewport_width * 0.33),
                    height=-1,
                    horizontal_scrollbar=True,
                    menubar=False,
                    border=False,
                    tag="child_window_drt_data",
                ):
                    with dpg.tab_bar(tag="tab_bar_drt_data"):
                        gui_utils.drt_table.table_update(config)

            # Plot display
            with dpg.child_window(
                width=-1,
                height=-1,
                horizontal_scrollbar=True,
                menubar=False,
                border=True,
                tag="child_window_drt_plot",
            ):
                with dpg.tab_bar(tag="tab_bar_drt_plot"):
                    with dpg.tab(label="Single", tag="tab_drt_plot_single"):
                        with dpg.tab_bar(tag="tab_bar_drt_plot_single"):
                            gui_utils.drt_plots.update_single_plots(config)

                    with dpg.tab(label="All", tag="tab_drt_plot_all"):
                        with dpg.tab_bar(tag="tab_bar_drt_plot_all"):
                            gui_utils.drt_plots.update_all_plots(config)

    # Select this tab
    # (tab_bar value is selected-tab tag; set_value is fine as long as tab_bar_main exists)
    if dpg.does_item_exist("tab_bar_main"):
        dpg.set_value("tab_bar_main", "tab_drt")
    gui_utils.file_list.display_file(None, config.display_file, config)

    dpg.set_viewport_resize_callback(update_child_window_size)
