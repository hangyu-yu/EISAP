import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util
import dearpygui.dearpygui as dpg

def load_parameters(sender, app_data, config):
    print("-- Loading DRT parameters...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Load the DRT parameters
            EIS_tmp.parameter["DRT"]["lambda"] = float(dpg.get_value("input_text_lambda"))

            # Load the optimal lambda parameters
            EIS_tmp.parameter["LambdaOpt"]["lambda_min"] = float(dpg.get_value("input_text_min_lambda"))
            EIS_tmp.parameter["LambdaOpt"]["lambda_max"] = float(dpg.get_value("input_text_max_lambda"))
            EIS_tmp.parameter["LambdaOpt"]["n"] = int(dpg.get_value("input_text_lambda_points"))

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

    dpg.set_value("text_optimal_lambda", f"{float(config.store[os.path.splitext(config.display_file)[0]]['EIS'].lambda_opt):.4e}")
    dpg.set_value("text_average_lambda", f"{float(lambdaopt_tmp / len(config.selected_files)):.4e}")
    print(f"---- Optimal lambda has been calculated successfully for {file_name_no_ext}.")
        
def process_data(sender, app_data, config):
    print("-- Processing DRT data based on tikhonov method...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            EIS_tmp.tknv()

            print(f"---- Data has been processed successfully for {file_name_no_ext}.")

def save_drt(sender, app_data, config):
    print("-- Saving DRT data...")
    if config.selected_files != [] and config.selected_files is not None:
        for file_name in config.selected_files:
            file_name_no_ext = os.path.splitext(file_name)[0]
            config.store[file_name_no_ext]['EIS'].save_data_DRT()