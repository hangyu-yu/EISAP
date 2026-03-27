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
    print("-- Loading DRT parameters...")
    lambda_target = "truncated"
    drt_method = None
    if dpg.does_item_exist("combo_lambda_target"):
        target_raw = dpg.get_value("combo_lambda_target")
        if target_raw is not None:
            lambda_target = normalize_lambda_target(target_raw, None)
    if dpg.does_item_exist("radio_drt_method"):
        drt_method = dpg.get_value("radio_drt_method")

    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            target_for_file = normalize_lambda_target(lambda_target, EIS_tmp)
            # Load the DRT parameters
            if EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Manual':
                EIS_tmp.parameter["DRT"]["lambda"] = float(dpg.get_value("input_text_lambda"))
            elif EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Optimal':
                EIS_tmp.parameter["DRT"]["lambda"] = EIS_tmp.lambda_opt

            # Load the optimal lambda parameters
            EIS_tmp.parameter["LambdaOpt"]["lambda_min"] = _read_numeric_input("input_text_min_lambda", float, 1e-7)
            EIS_tmp.parameter["LambdaOpt"]["lambda_max"] = _read_numeric_input("input_text_max_lambda", float, 0.2)
            EIS_tmp.parameter["LambdaOpt"]["n"] = _read_numeric_input("input_text_lambda_points", int, 100)
            EIS_tmp.parameter["LambdaOpt"]["target"] = target_for_file

            # Load RBF-DRT parameters
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
                EIS_tmp.parameter["DRT_RBF"]["fit_inductance"] = bool(
                    dpg.get_value("check_box_rbf_fit_inductance")
                )
            if drt_method is not None:
                EIS_tmp.parameter["DRT_RBF"]["enabled"] = (drt_method == "RBF-DRT")

            print(f"---- DRT parameters have been loaded successfully for {file_name_no_ext}.")
    
def lambdaopt(sender, app_data, config):
    lambdaopt_tmp = 0
    print("-- Calculating the optimal lambda...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            lambda_input, lambda_source = _get_lambdaopt_input_data(EIS_tmp)
            EIS_tmp.lambdaOPT(lambda_input)
            lambdaopt_tmp = lambdaopt_tmp + EIS_tmp.lambda_opt
            print(f"---- LambdaOPT source for {file_name_no_ext}: {lambda_source}")

    dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.3e}")
    dpg.set_value("text_average_lambda", f"{float(lambdaopt_tmp / len(config.selected_files)):.3e}")

    # Refresh plots so L-curve appears immediately in Single/All tabs.
    import src.GUI.Utils as gui_utils

    if dpg.does_item_exist("tab_bar_drt_plot_single"):
        try:
            gui_utils.drt_plots.update_single_plots(config)
        except Exception as e:
            print(f"---- Warning: Failed to refresh Single L-curve plots after lambda computation: {e}")
            print(traceback.format_exc())

    if dpg.does_item_exist("tab_bar_drt_plot_all"):
        try:
            gui_utils.drt_plots.update_all_plots(config)
        except Exception as e:
            print(f"---- Warning: Failed to refresh All L-curve plots after lambda computation: {e}")
            print(traceback.format_exc())

    print(f"---- Optimal lambda has been calculated successfully for all selected files.")
        
def process_data(sender, app_data, config):
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            rbf_enabled = EIS_tmp.parameter.get('DRT_RBF', {}).get('enabled', False)

            if rbf_enabled:
                print(f"-- Processing DRT data using Tikhonov + RBF-DRT for {file_name_no_ext}...")
                # Keep Tikhonov data up-to-date even in RBF mode.
                if EIS_tmp.parameter["DRT"]["tknv_pos"]:
                    EIS_tmp.tknv_pos()
                else:
                    EIS_tmp.tknv()
                EIS_tmp.rbf()
            else:
                print(f"-- Processing DRT data using Tikhonov method for {file_name_no_ext}...")
                if EIS_tmp.parameter["DRT"]["tknv_pos"]:
                    EIS_tmp.tknv_pos()
                else:
                    EIS_tmp.tknv()

            print(f"---- Data has been processed successfully for {file_name_no_ext}.")

    if config.display_file:
        display_key = os.path.splitext(config.display_file)[0]
        if display_key in config.store and 'EIS' in config.store[display_key]:
            refresh_lambda_target_combo(config.store[display_key]['EIS'])

def save_drt(sender, app_data, config, EIS):
    print("-- Saving DRT data...")
    EIS.backup_folder_to_temp_zip('DRT', 'DRT_backup.zip')
    if config.selected_files != [] and config.selected_files is not None:
        for file_name in config.selected_files:
            try:
                file_name_no_ext = os.path.splitext(file_name)[0]
                config.store[file_name_no_ext]['EIS'].file_folder = config.folder_path
                config.store[file_name_no_ext]['EIS'].save_data_DRT()
            except Exception as e:
                print(f"[Warning] DRT-save: File {file_name} is empty")