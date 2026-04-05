import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util
import traceback
import dearpygui.dearpygui as dpg


_LAMBDA_TARGET_BASE_ITEMS = ["truncated", "lccorrect", "smooth", "extrapolation"]


def _is_valid_eis_dataset(dataset):
    if not isinstance(dataset, dict):
        return False
    f = dataset.get("f")
    re = dataset.get("Re")
    im = dataset.get("Im")
    if f is None or re is None or im is None:
        return False
    try:
        f_len = len(f)
        return f_len > 0 and len(re) == f_len and len(im) == f_len
    except TypeError:
        return False


def has_valid_zhit_lambda_target(eis_obj):
    if not hasattr(eis_obj, "get_zhit_smooth_eis_data"):
        return False
    try:
        return _is_valid_eis_dataset(eis_obj.get_zhit_smooth_eis_data())
    except Exception:
        return False


def get_lambda_target_items(eis_obj):
    items = list(_LAMBDA_TARGET_BASE_ITEMS)
    if has_valid_zhit_lambda_target(eis_obj):
        items.append("zhit")
    return items


def normalize_lambda_target(target, eis_obj=None):
    target_norm = str(target).lower().strip() if target is not None else "truncated"
    allowed = set(_LAMBDA_TARGET_BASE_ITEMS)
    if eis_obj is None or has_valid_zhit_lambda_target(eis_obj):
        allowed.add("zhit")
    if target_norm not in allowed:
        target_norm = "truncated"
    return target_norm


def refresh_lambda_target_combo(eis_obj):
    if not dpg.does_item_exist("combo_lambda_target"):
        return
    items = get_lambda_target_items(eis_obj)
    dpg.configure_item("combo_lambda_target", items=items)
    current_value = dpg.get_value("combo_lambda_target")
    target_norm = normalize_lambda_target(current_value, eis_obj)
    dpg.set_value("combo_lambda_target", target_norm)
    if hasattr(eis_obj, "parameter") and isinstance(eis_obj.parameter, dict):
        eis_obj.parameter.setdefault("LambdaOpt", {})["target"] = target_norm


def _read_numeric_input(widget_id, cast, default):
    value = dpg.get_value(widget_id)
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return cast(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() in {"not available", "n/a", "na"}:
            return default
        try:
            return cast(text)
        except (TypeError, ValueError):
            return default
    return default


def _get_lambdaopt_input_data(eis_obj):
    lambda_target = "truncated"
    if hasattr(eis_obj, "parameter") and isinstance(eis_obj.parameter, dict):
        lambda_target = normalize_lambda_target(
            eis_obj.parameter.get("LambdaOpt", {}).get("target", "truncated"),
            eis_obj,
        )

    dataset_map = {
        "truncated": (getattr(eis_obj, "truncated", None), "truncated"),
        "lccorrect": (getattr(eis_obj, "LCcorrect", None), "lccorrect"),
        "smooth": (getattr(eis_obj, "smooth", None), "smooth"),
        "extrapolation": (getattr(eis_obj, "extrapolation", None), "extrapolation"),
    }

    if lambda_target == "zhit" and has_valid_zhit_lambda_target(eis_obj):
        zhit_data = eis_obj.get_zhit_smooth_eis_data()
        return zhit_data, "zhit"

    if lambda_target == "zhit":
        print("---- LambdaOPT target 'zhit' requested but ZHIT data is unavailable; fallback to truncated.")
    else:
        target_data, _ = dataset_map.get(lambda_target, (None, lambda_target))
        if _is_valid_eis_dataset(target_data):
            return target_data, lambda_target
        print(f"---- LambdaOPT target '{lambda_target}' is unavailable; fallback to truncated.")

    truncated_data = getattr(eis_obj, "truncated", None)
    if _is_valid_eis_dataset(truncated_data):
        return truncated_data, "truncated"

    for candidate, (candidate_data, _) in dataset_map.items():
        if _is_valid_eis_dataset(candidate_data):
            return candidate_data, candidate

    raise ValueError("No valid EIS dataset is available for LambdaOPT.")

def load_parameters(sender, app_data, config):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "DRT — Load Parameters", "Loading DRT parameters...",
        max(1, len(config.selected_files)),
    )
    lambda_target = "truncated"
    drt_method = None
    if dpg.does_item_exist("combo_lambda_target"):
        target_raw = dpg.get_value("combo_lambda_target")
        if target_raw is not None:
            lambda_target = normalize_lambda_target(target_raw, None)
    if dpg.does_item_exist("radio_drt_method"):
        drt_method = dpg.get_value("radio_drt_method")

    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            target_for_file = normalize_lambda_target(lambda_target, EIS_tmp)
            if EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Manual':
                EIS_tmp.parameter["DRT"]["lambda"] = float(dpg.get_value("input_text_lambda"))
            elif EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Optimal':
                EIS_tmp.parameter["DRT"]["lambda"] = EIS_tmp.lambda_opt
            EIS_tmp.parameter["LambdaOpt"]["lambda_min"] = _read_numeric_input("input_text_min_lambda", float, 1e-7)
            EIS_tmp.parameter["LambdaOpt"]["lambda_max"] = _read_numeric_input("input_text_max_lambda", float, 0.2)
            EIS_tmp.parameter["LambdaOpt"]["n"] = _read_numeric_input("input_text_lambda_points", int, 100)
            EIS_tmp.parameter["LambdaOpt"]["target"] = target_for_file
            if dpg.does_item_exist("input_text_rbf_lambda"):
                EIS_tmp.parameter["DRT_RBF"]["lambda"] = _read_numeric_input("input_text_rbf_lambda", float, 1e-3)
            if dpg.does_item_exist("input_text_rbf_coeff"):
                EIS_tmp.parameter["DRT_RBF"]["coeff"] = _read_numeric_input("input_text_rbf_coeff", float, 0.5)
            if dpg.does_item_exist("combo_rbf_type"):
                EIS_tmp.parameter["DRT_RBF"]["rbf_type"] = dpg.get_value("combo_rbf_type")
            if dpg.does_item_exist("combo_rbf_shape_control"):
                EIS_tmp.parameter["DRT_RBF"]["shape_control"] = dpg.get_value("combo_rbf_shape_control")
            if dpg.does_item_exist("combo_rbf_der_used"):
                EIS_tmp.parameter["DRT_RBF"]["der_used"] = dpg.get_value("combo_rbf_der_used")
            if dpg.does_item_exist("combo_rbf_method"):
                EIS_tmp.parameter["DRT_RBF"]["method"] = dpg.get_value("combo_rbf_method")
            if dpg.does_item_exist("check_box_rbf_fit_inductance"):
                EIS_tmp.parameter["DRT_RBF"]["fit_inductance"] = bool(dpg.get_value("check_box_rbf_fit_inductance"))
            if drt_method is not None:
                EIS_tmp.parameter["DRT_RBF"]["enabled"] = (drt_method == "RBF-DRT")
            _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] DRT load_parameters:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("DRT — Load Parameters Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)
def lambdaopt(sender, app_data, config):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "DRT — Compute Lambda", "Computing optimal lambda...",
        max(1, len(config.selected_files)),
    )
    lambdaopt_tmp = 0
    _success = False
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            lambda_input, lambda_source = _get_lambdaopt_input_data(EIS_tmp)
            EIS_tmp.lambdaOPT(lambda_input)
            lambdaopt_tmp += EIS_tmp.lambda_opt
            _pm.update_progress(progress, i + 1, file_name)
        _success = True
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] DRT lambdaopt:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("DRT — Compute Lambda Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

    if not _success:
        return
    dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.3e}")
    dpg.set_value("text_average_lambda", f"{float(lambdaopt_tmp / len(config.selected_files)):.3e}")

    import src.GUI.Utils as gui_utils
    if dpg.does_item_exist("tab_bar_drt_plot_single"):
        try:
            gui_utils.drt_plots.update_single_plots(config)
        except Exception as _ep:
            import traceback as _tb
            print(f"[Warning] DRT lambdaopt — single-plot refresh failed:\n{_tb.format_exc()}")
    if dpg.does_item_exist("tab_bar_drt_plot_all"):
        try:
            gui_utils.drt_plots.update_all_plots(config)
        except Exception as _ep:
            import traceback as _tb
            print(f"[Warning] DRT lambdaopt — all-plot refresh failed:\n{_tb.format_exc()}")
        
def process_data(sender, app_data, config):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "DRT — Process Data", "Processing DRT data...",
        max(1, len(config.selected_files)),
    )
    _success = False
    _current_file = ""
    # Use the GUI radio button as the single source of truth for method selection.
    # This ensures all selected files are processed with the same method regardless
    # of whether their individual 'enabled' flag was synced before this call.
    rbf_from_gui = dpg.get_value("radio_drt_method") == "RBF-DRT" if dpg.does_item_exist("radio_drt_method") else None
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Sync the per-file enabled flag from the GUI before computing.
            if rbf_from_gui is not None:
                EIS_tmp.parameter['DRT_RBF']['enabled'] = rbf_from_gui
            rbf_enabled = EIS_tmp.parameter.get('DRT_RBF', {}).get('enabled', False)
            if rbf_enabled:
                if EIS_tmp.parameter["DRT"]["tknv_pos"]:
                    EIS_tmp.tknv_pos()
                else:
                    EIS_tmp.tknv()
                EIS_tmp.rbf()
            else:
                if EIS_tmp.parameter["DRT"]["tknv_pos"]:
                    EIS_tmp.tknv_pos()
                else:
                    EIS_tmp.tknv()
            _pm.update_progress(progress, i + 1, file_name)
        _success = True
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] DRT process_data:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("DRT — Process Data Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

    if not _success:
        return
    if config.display_file:
        display_key = os.path.splitext(config.display_file)[0]
        if display_key in config.store and 'EIS' in config.store[display_key]:
            refresh_lambda_target_combo(config.store[display_key]['EIS'])

    # Keep CNLS fit DRT view in sync after DRT re-processing.
    if dpg.does_item_exist("tab_cnls"):
        import src.GUI.Utils as gui_utils
        if dpg.does_item_exist("tab_bar_cnls_plot_single"):
            try:
                gui_utils.cnls_plots.update_single_plots(config)
            except Exception as _ep:
                import traceback as _tb
                print(f"[Warning] DRT process_data — CNLS single-plot refresh failed:\n{_tb.format_exc()}")
        if dpg.does_item_exist("tab_bar_cnls_plot_all"):
            try:
                gui_utils.cnls_plots.update_all_plots(config)
            except Exception as _ep:
                import traceback as _tb
                print(f"[Warning] DRT process_data — CNLS all-plot refresh failed:\n{_tb.format_exc()}")

def save_drt(sender, app_data, config, EIS):
    import src.GUI.Utils.progress_modal as _pm
    n = len(config.selected_files) if config.selected_files else 0
    progress = _pm.open_progress(
        "DRT — Save", "Saving DRT data...", max(1, n),
    )
    try:
        EIS.backup_folder_to_temp_zip('DRT', 'DRT_backup.zip')
        _current_file = ""
        if config.selected_files:
            for i, file_name in enumerate(config.selected_files):
                _current_file = file_name
                _pm.update_progress(progress, i, file_name)
                try:
                    file_name_no_ext = os.path.splitext(file_name)[0]
                    config.store[file_name_no_ext]['EIS'].file_folder = config.folder_path
                    config.store[file_name_no_ext]['EIS'].save_data_DRT()
                except Exception as _ei:
                    import traceback as _tb
                    print(f"[Warning] DRT-save failed for {file_name}: {_ei}\n{_tb.format_exc()}")
                    _pm.show_error_dialog("DRT — Save Warning", f"'{file_name}' could not be saved:\n{_ei}")
                _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] DRT save_drt:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("DRT — Save Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)