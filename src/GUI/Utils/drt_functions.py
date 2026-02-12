import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util
import dearpygui.dearpygui as dpg


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

def load_parameters(sender, app_data, config):
    print("-- Loading DRT parameters...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Load the DRT parameters
            if EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Manual':
                EIS_tmp.parameter["DRT"]["lambda"] = float(dpg.get_value("input_text_lambda"))
            elif EIS_tmp.parameter["DRT"]["Lambda_selection"] == 'Optimal':
                EIS_tmp.parameter["DRT"]["lambda"] = EIS_tmp.lambda_opt

            # Load the optimal lambda parameters
            EIS_tmp.parameter["LambdaOpt"]["lambda_min"] = _read_numeric_input("input_text_min_lambda", float, 1e-7)
            EIS_tmp.parameter["LambdaOpt"]["lambda_max"] = _read_numeric_input("input_text_max_lambda", float, 0.2)
            EIS_tmp.parameter["LambdaOpt"]["n"] = _read_numeric_input("input_text_lambda_points", int, 100)

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
            EIS_tmp.lambdaOPT(EIS_tmp.truncated)
            lambdaopt_tmp = lambdaopt_tmp + EIS_tmp.lambda_opt

    dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.3e}")
    dpg.set_value("text_average_lambda", f"{float(lambdaopt_tmp / len(config.selected_files)):.3e}")
    print(f"---- Optimal lambda has been calculated successfully for all selected files.")
        
def process_data(sender, app_data, config):
    print("-- Processing DRT data based on tikhonov method...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            if EIS_tmp.parameter["DRT"]["tknv_pos"]:
                EIS_tmp.tknv_pos()
            else:
                EIS_tmp.tknv()

            print(f"---- Data has been processed successfully for {file_name_no_ext}.")

def save_drt(sender, app_data, config):
    print("-- Saving DRT data...")
    if config.selected_files != [] and config.selected_files is not None:
        for file_name in config.selected_files:
            try:
                file_name_no_ext = os.path.splitext(file_name)[0]
                config.store[file_name_no_ext]['EIS'].file_folder = config.folder_path
                config.store[file_name_no_ext]['EIS'].save_data_DRT()
            except Exception as e:
                print(f"[Warning] DRT-save: File {file_name} is empty")