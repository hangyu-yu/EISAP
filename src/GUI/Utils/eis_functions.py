import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util
import dearpygui.dearpygui as dpg

def call_function(file_path, *args, **kwargs):
    """Directly call a function with the same name as the Python file"""
    # Extract the module name (remove path and .py)
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Dynamically load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    # Retrieve and call the function with the same name
    func = getattr(module, module_name)
    return func(*args, **kwargs)  # Directly execute and return the result

def data_import(sender, app_data, config, EIS):
    for file_name in config.selected_files:
        file_path = os.path.join(config.folder_path, file_name)

        if file_path is None:
            raise FileNotFoundError('The specified file does not exist.')
        else: 
            metadata,data = call_function(config.data_import_function, file_path)
            file_name_no_ext = os.path.splitext(file_name)[0]
            config.store[file_name_no_ext] = {}
            config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            EIS_tmp.filename = file_name
            print('---- Data imported:', file_path)
        EIS_tmp.raw['Re'] = data['Re/Ohm'].to_numpy()
        EIS_tmp.raw['Im'] = data['Im/Ohm'].to_numpy()
        EIS_tmp.raw['Z'] = EIS_tmp.raw['Re'] + 1j * EIS_tmp.raw['Im']
        EIS_tmp.raw['f'] = data['Frequency/Hz'].to_numpy()
        if 'Significance' in data.columns:
            EIS_tmp.raw['significance'] = data['Significance'].to_numpy()
        EIS_tmp.info = metadata
        EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, EIS_tmp.parameter['Sample'])

        if dpg.does_item_exist("tab_eis_raw_data_table"):
            dpg.configure_item("combo_eis_plot_file", items=config.selected_files)
            config.display_file = config.selected_files[0] if config.selected_files else ""
            dpg.set_value("combo_eis_plot_file", config.display_file)

def load_parameters(sender, app_data, config, EIS):
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Load the parameter for the general settings
            EIS_tmp.parameter["Sample"]["CellArea"] = float(dpg.get_value("CellArea"))
            EIS_tmp.parameter["Sample"]["n_cell"] = int(dpg.get_value("n_cell"))
            EIS_tmp.parameter["Sample"]["instrument_type"] = dpg.get_value("instrument_type")
            EIS_tmp.parameter["Preprocessing"]["num_cut_upper"] = int(dpg.get_value("num_cut_upper"))
            EIS_tmp.parameter["Preprocessing"]["num_cut_lower"] = int(dpg.get_value("num_cut_lower"))
            EIS_tmp.parameter["RM_significance"]["sig_threshold"] = float(dpg.get_value("sig_threshold"))
            EIS_tmp.parameter["RM_significance"]["rm_significance"] = dpg.get_value("rm_significance")
            EIS_tmp.parameter["Rmoutliers"]["Rmoutliers"] = dpg.get_value("rm_outliers")

            # Load the KK parameters
            EIS_tmp.parameter["KK"]["nRCmax"] = int(dpg.get_value("nRCmax"))
            EIS_tmp.parameter["KK"]["nRC"] = int(dpg.get_value("nRC"))
            EIS_tmp.parameter["KK"]["kk_threshold"] = float(dpg.get_value("kk_threshold"))
            EIS_tmp.parameter["KK"]["mu_threshold"] = float(dpg.get_value("mu_threshold"))
            EIS_tmp.parameter["KK"]["KK_test"] = dpg.get_value("KK_test")
            EIS_tmp.parameter["KK"]["KK_type"] = EIS.parameter["KK"]["KK_type"]
            EIS_tmp.parameter["KK"]["RmNonKK"] = dpg.get_value("RmNonKK")

            # Load the EIS parameters
            EIS_tmp.parameter["Smoothing"]["PointsPerDecade"] = int(dpg.get_value("Smooth_PointsPerDecade"))
            EIS_tmp.parameter["Extrapolation"]["fmin"] = float(dpg.get_value("extrapolation_fmin"))
            EIS_tmp.parameter["Extrapolation"]["fmax"] = float(dpg.get_value("extrapolation_fmax"))
            EIS_tmp.parameter["Extrapolation"]["PointsPerDecade"] = int(dpg.get_value("Extrapolation_PointsPerDecade"))
            print(f"---- EIS parameters have been loaded successfully for {file_name_no_ext}.")

def process_data(sender, app_data, config, EIS):
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # 01 - Data cut based on the upper and lower numbers
            EIS_tmp.rm_hfc_lfc()

            # 02 - Data cut based on the significance values
            if EIS_tmp.parameter['RM_significance']['rm_significance']:
                EIS_tmp.rm_significance()

            # 03 - Data cut due to outliers
            if EIS_tmp.parameter['Rmoutliers']['Rmoutliers']:
                EIS_tmp.rm_outliers()

            # 04 - Data cut based on KK criterion
            if EIS_tmp.parameter['KKpreprocess']['OptimalCut']:
                EIS_tmp.Linear_KK_opt_mu_cut(EIS_tmp.truncated, EIS_tmp.parameter['KKpreprocess'])

            # 05 - KK test
            if EIS_tmp.parameter['KK']['KK_test']:
                EIS_tmp.KK_test(EIS_tmp.truncated)
            
            # 06 - Data cut based on KK residual
            if EIS_tmp.parameter['KK']['RmNonKK']:
                EIS_tmp.rm_auto_KK()
                EIS_tmp.KK_test(EIS_tmp.truncated)
            
            # 06 - Get smoothed data, LCcorrected data, and extrapolated data
            EIS_tmp.parameter['Smoothing']['fmax'] = max(EIS_tmp.truncated['f'])
            EIS_tmp.parameter['Smoothing']['fmin'] = min(EIS_tmp.truncated['f'])
            EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
            EIS_tmp.store['RsLCinv_kk']['L'] = 0
            EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0
            EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
            EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

            print(f"---- Data has been processed successfully for {file_name_no_ext}.")

def save_eis(sender, app_data, config):
    print("-- Saving EIS data...")
    if config.selected_files != [] and config.selected_files is not None:
        for file_name in config.selected_files:
            file_name_no_ext = os.path.splitext(file_name)[0]
            config.store[file_name_no_ext]['EIS'].file_folder = config.folder_path
            config.store[file_name_no_ext]['EIS'].save_data_EIS()