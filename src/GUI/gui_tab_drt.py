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
    def _target_files_for_update():
        if config.selected_files:
            return list(config.selected_files)
        if config.display_file:
            return [config.display_file]
        return []

    def _get_display_eis_obj():
        if config.display_file:
            key = os.path.splitext(config.display_file)[0]
            if key in config.store and "EIS" in config.store[key]:
                return config.store[key]["EIS"]
        if config.selected_files:
            key = os.path.splitext(config.selected_files[0])[0]
            if key in config.store and "EIS" in config.store[key]:
                return config.store[key]["EIS"]
        return None

    mode = False
    auto_lambda = 0.05 if app_data else 5e-4

    for file_name in _target_files_for_update():
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            continue
        else:
            EIS_tmp = config.store[file_name_no_ext]["EIS"]
            # Keep lambda coupled to tknv_pos mode when in Manual mode.
            if EIS_tmp.parameter["DRT"].get("Lambda_selection", "Manual") != "Optimal":
                EIS_tmp.parameter["DRT"]["lambda"] = auto_lambda
            if app_data:
                mode = True
                if dpg.does_item_exist("input_text_lambda"):
                    # Keep lambda mode behavior consistent: manual uses numeric value, optimal shows locked text.
                    if dpg.get_value("check_box_lambda_mode"):
                        dpg.configure_item("input_text_lambda", enabled=False)
                        dpg.set_value("input_text_lambda", "Optimal")
                    else:
                        dpg.configure_item("input_text_lambda", enabled=True)
                        dpg.set_value("input_text_lambda", EIS_tmp.parameter["DRT"]["lambda"])
                dpg.configure_item("check_box_lambda_mode", enabled=True)
                dpg.configure_item("input_text_max_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_max"])
                dpg.configure_item("input_text_min_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_min"])
                dpg.configure_item("input_text_lambda_points", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["n"])
            else:
                mode = False
                if dpg.does_item_exist("input_text_lambda"):
                    if dpg.get_value("check_box_lambda_mode"):
                        dpg.configure_item("input_text_lambda", enabled=False)
                        dpg.set_value("input_text_lambda", "Optimal")
                    else:
                        dpg.configure_item("input_text_lambda", enabled=True)
                        dpg.set_value("input_text_lambda", EIS_tmp.parameter["DRT"]["lambda"])
                dpg.configure_item("check_box_lambda_mode", enabled=True)
                dpg.configure_item("input_text_max_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_max"])
                dpg.configure_item("input_text_min_lambda", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["lambda_min"])
                dpg.configure_item("input_text_lambda_points", enabled=True, default_value=EIS_tmp.parameter["LambdaOpt"]["n"])
            EIS_tmp.parameter["DRT"]["tknv_pos"] = mode

    # Keep the visible lambda in sync with displayed file after toggle.
    if dpg.does_item_exist("input_text_lambda") and not dpg.get_value("check_box_lambda_mode"):
        display_eis = _get_display_eis_obj()
        if display_eis is not None:
            dpg.set_value("input_text_lambda", display_eis.parameter["DRT"]["lambda"])

    print(f"-- Tikhonov positive mode set to {mode}")


def lambda_target_callback(sender, app_data, EIS, config):
    """
    Callback function for selecting lambda optimization target dataset.
    """
    target = str(app_data).lower().strip() if app_data is not None else "truncated"
    if target not in {"truncated", "lccorrect", "smooth", "extrapolation", "zhit"}:
        target = "truncated"

    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError("The specified file is not loaded or EIS processing is not done.")
        eis_obj = config.store[file_name_no_ext]["EIS"]
        eis_obj.parameter["LambdaOpt"]["target"] = gui_utils.drt_functions.normalize_lambda_target(target, eis_obj)

    print(f"-- Lambda target set to {target}")

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
    import src.GUI.Utils.progress_modal as _pm
    try:
        gui_utils.drt_functions.process_data(sender, app_data, config)
        gui_utils.drt_table.table_update(config)
        gui_utils.drt_plots.update_single_plots(config)

        if _ensure_plot_tab_bars_exist():
            dpg.delete_item("tab_bar_drt_plot_all", children_only=True)
            gui_utils.drt_plots.update_all_plots(config)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] DRT callback_process_data:\n{_tb.format_exc()}")
        _pm.show_error_dialog("DRT — Process Data Error", f"{type(_e).__name__}: {_e}", file_hint=config.display_file)

def plot_drt_tau_callback(sender, app_data, config):
    """
    Callback function to update the DRT plot with tau values.
    """
    gui_utils.drt_plots.update_single_plots(config)
    gui_utils.drt_plots.update_all_plots(config)

def _drt_method_switch_callback(sender, app_data, EIS, config):
    """
    Toggle between Tikhonov and RBF-DRT.
    Updates parameter['DRT_RBF']['enabled'] for all selected files and
    switches the active parameter tab so the correct controls are visible.
    """
    use_rbf = (app_data == "RBF-DRT")

    target_files = list(config.selected_files) if config.selected_files else []
    if not target_files and config.display_file:
        target_files = [config.display_file]

    for file_name in target_files:
        key = os.path.splitext(file_name)[0]
        if key in config.store and "EIS" in config.store[key]:
            config.store[key]["EIS"].parameter["DRT_RBF"]["enabled"] = use_rbf

    # Switch the visible parameter tab to match the selected method
    if dpg.does_item_exist("tab_bar_drt_params"):
        target_tab = "tab_drt_params_rbf" if use_rbf else "tab_drt_params_tknv"
        if dpg.does_item_exist(target_tab):
            dpg.set_value("tab_bar_drt_params", target_tab)

    # Redraw plots using the selected method's result set on existing tabs.
    try:
        gui_utils.drt_table.table_update(config)
    except Exception as e:
        print(f"-- Warning: failed to refresh DRT table after method switch: {e}")

    try:
        gui_utils.drt_plots.update_single_plots(config)
    except Exception as e:
        print(f"-- Warning: failed to refresh single DRT plots after method switch: {e}")

    try:
        if dpg.does_item_exist("tab_bar_drt_plot_all"):
            dpg.delete_item("tab_bar_drt_plot_all", children_only=True)
        gui_utils.drt_plots.update_all_plots(config)
    except Exception as e:
        print(f"-- Warning: failed to refresh all DRT plots after method switch: {e}")

    print(f"-- DRT method set to {'RBF-DRT' if use_rbf else 'Tikhonov'}")


def _get_drt_default_eis(config, fallback_eis):
    """Return the EIS object used to initialize DRT parameter widgets."""
    candidate_files = []
    if config.display_file:
        candidate_files.append(config.display_file)
    if config.selected_files:
        candidate_files.extend(config.selected_files)

    for file_name in candidate_files:
        key = os.path.splitext(file_name)[0]
        if key in config.store and "EIS" in config.store[key]:
            return config.store[key]["EIS"]

    return fallback_eis


def gui_tab_drt(config, EIS, CNLS):
    config.save_config()

    # Fast path: if DRT tab already exists, just switch to it and avoid expensive rebuild.
    if dpg.does_item_exist("tab_drt"):
        if dpg.does_item_exist("tab_bar_main"):
            dpg.set_value("tab_bar_main", "tab_drt")
        try:
            gui_utils.file_list.display_file(
                None,
                config.display_file,
                config,
                refresh_eis_tab=False,
                refresh_drt_tab=True,
                refresh_cnls_tab=False,
            )
        except Exception:
            pass
        update_child_window_size()
        return

    # Initialize defaults from the currently displayed/selected file when available.
    EIS = _get_drt_default_eis(config, EIS)

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
                    try:
                        gui_utils.file_list.update_file_list(
                            config,
                            "child_window_file_list_drt",
                            EIS,
                            CNLS,
                            import_history=False,
                            show_progress=False,
                            run_alignment=False,
                        )
                    except Exception as e:
                        print(f"[Warning] DRT file list init failed: {e}")

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
                            dpg.add_checkbox(
                                tag="check_box_drt_tau",
                                label="x-tau",
                                default_value = False,
                                callback=lambda sender, app_data: plot_drt_tau_callback(sender, app_data, config),
                            )

                    # ── Method selector ───────────────────────────────────────
                    rbf_enabled_default = EIS.parameter.get("DRT_RBF", {}).get("enabled", False)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Method:")
                        dpg.add_radio_button(
                            tag="radio_drt_method",
                            items=["Tikhonov", "RBF-DRT"],
                            default_value="RBF-DRT" if rbf_enabled_default else "Tikhonov",
                            horizontal=True,
                            callback=lambda s, a: _drt_method_switch_callback(s, a, EIS, config),
                        )

                    dpg.add_separator()

                    # ── Parameter tab bar: Tikhonov | RBF ────────────────────
                    drt_params_default_tab = "tab_drt_params_rbf" if rbf_enabled_default else "tab_drt_params_tknv"
                    with dpg.tab_bar(tag="tab_bar_drt_params"):

                        # ── Tikhonov tab ──────────────────────────────────────
                        with dpg.tab(label="Tikhonov", tag="tab_drt_params_tknv"):
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
                                        default_value=EIS.parameter["LambdaOpt"]["lambda_min"],
                                        enabled=True,
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("")
                                    dpg.add_text("Max. lambda:", tag="text_max_lambda")
                                    dpg.add_input_text(
                                        tag="input_text_max_lambda",
                                        default_value=EIS.parameter["LambdaOpt"]["lambda_max"],
                                        enabled=True,
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("")
                                    dpg.add_text("Lambda points:", tag="text_lambda_points")
                                    dpg.add_input_text(
                                        tag="input_text_lambda_points",
                                        default_value=EIS.parameter["LambdaOpt"]["n"],
                                        enabled=True,
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("")
                                    dpg.add_text("Lambda target:")
                                    lambda_target_items = gui_utils.drt_functions.get_lambda_target_items(EIS)
                                    lambda_target_default = gui_utils.drt_functions.normalize_lambda_target(
                                        EIS.parameter["LambdaOpt"].get("target", "truncated"),
                                        EIS,
                                    )
                                    dpg.add_combo(
                                        tag="combo_lambda_target",
                                        items=lambda_target_items,
                                        default_value=lambda_target_default,
                                        callback=lambda sender, app_data: lambda_target_callback(sender, app_data, EIS, config),
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

                        # ── RBF-DRT tab ───────────────────────────────────────
                        with dpg.tab(label="RBF-DRT", tag="tab_drt_params_rbf"):
                            rbf_p = EIS.parameter.get("DRT_RBF", {})
                            with dpg.table(
                                header_row=False,
                                borders_innerH=False,
                                row_background=False,
                                policy=dpg.mvTable_SizingStretchProp,
                            ):
                                dpg.add_table_column(width_fixed=True, init_width_or_weight=int(viewport_width * 0.10))
                                dpg.add_table_column(width_stretch=True)

                                with dpg.table_row():
                                    dpg.add_text("Lambda:")
                                    dpg.add_input_text(
                                        tag="input_text_rbf_lambda",
                                        default_value=rbf_p.get("lambda", 1e-3),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("RBF type:")
                                    dpg.add_combo(
                                        tag="combo_rbf_type",
                                        items=["Gaussian", "C0 Matern", "C2 Matern", "C4 Matern",
                                               "C6 Matern", "Inverse quadratic", "Cauchy", "Piecewise linear"],
                                        default_value=rbf_p.get("rbf_type", "Gaussian"),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("Coeff (FWHM):")
                                    dpg.add_input_text(
                                        tag="input_text_rbf_coeff",
                                        default_value=rbf_p.get("coeff", 0.5),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("Shape ctrl:")
                                    dpg.add_combo(
                                        tag="combo_rbf_shape_control",
                                        items=["FWHM Coefficient", "Shape Factor"],
                                        default_value=rbf_p.get("shape_control", "FWHM Coefficient"),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("Derivative:")
                                    dpg.add_combo(
                                        tag="combo_rbf_der_used",
                                        items=["1st order", "2nd order"],
                                        default_value=rbf_p.get("der_used", "1st order"),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("Method:")
                                    dpg.add_combo(
                                        tag="combo_rbf_method",
                                        items=["ridge", "bayes"],
                                        default_value=rbf_p.get("method", "ridge"),
                                        width=-1,
                                    )

                                with dpg.table_row():
                                    dpg.add_text("Fit inductance:")
                                    dpg.add_checkbox(
                                        tag="check_box_rbf_fit_inductance",
                                        default_value=rbf_p.get("fit_inductance", False),
                                    )

                    if dpg.does_item_exist("tab_bar_drt_params") and dpg.does_item_exist(drt_params_default_tab):
                        dpg.set_value("tab_bar_drt_params", drt_params_default_tab)

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
                            callback=lambda s, a: gui_utils.drt_functions.save_drt(s, a, config, EIS),
                        )
                        dpg.bind_item_theme("Button_Save_DRT", blue_button_theme)

                    with dpg.group(horizontal=True, tag="group_drt_display_file"):
                        dpg.add_text("Displayed file:")
                        dpg.add_button(arrow=True, direction=dpg.mvDir_Left, tag="button_prev_display_file_drt",
                                       callback=lambda: gui_utils.file_list.step_display_file(config, -1))
                        dpg.add_button(arrow=True, direction=dpg.mvDir_Right, tag="button_next_display_file_drt",
                                       callback=lambda: gui_utils.file_list.step_display_file(config, +1))
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
                        try:
                            gui_utils.drt_table.table_update(config)
                        except Exception as e:
                            print(f"[Warning] DRT table init failed: {e}")

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
                            try:
                                gui_utils.drt_plots.update_single_plots(config)
                            except Exception as e:
                                print(f"[Warning] DRT single plot init failed: {e}")

                    with dpg.tab(label="All", tag="tab_drt_plot_all"):
                        with dpg.tab_bar(tag="tab_bar_drt_plot_all"):
                            try:
                                gui_utils.drt_plots.update_all_plots(config)
                            except Exception as e:
                                print(f"[Warning] DRT all plot init failed: {e}")

    # Select this tab
    # (tab_bar value is selected-tab tag; set_value is fine as long as tab_bar_main exists)
    if dpg.does_item_exist("tab_bar_main"):
        dpg.set_value("tab_bar_main", "tab_drt")
    try:
        gui_utils.file_list.display_file(
            None,
            config.display_file,
            config,
            refresh_eis_tab=False,
            refresh_drt_tab=True,
            refresh_cnls_tab=False,
        )
    except Exception as e:
        print(f"[Warning] DRT display_file refresh failed: {e}")
    update_child_window_size()
