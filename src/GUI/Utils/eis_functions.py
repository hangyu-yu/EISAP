import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util

def call_function(file_path, *args, **kwargs):
    """Directly call a function with the same name as the Python file"""
    # Extract the module name (remove path and .py)
    module_name = file_path.split("/")[-1].replace(".py", "")
    
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
            filename = os.path.basename(file_path)
            config.store[filename] = copy.deepcopy(EIS)
            EIS_tmp = config.store[filename]
            EIS_tmp.filename = filename
            print('---- File loaded:', file_path)
        EIS_tmp.raw['Re'] = data['Re/Ohm'].to_numpy()
        EIS_tmp.raw['Im'] = data['Im/Ohm'].to_numpy()
        EIS_tmp.raw['Z'] = data['impedance/Ohm'].to_numpy()
        EIS_tmp.raw['f'] = data['Frequency/Hz'].to_numpy()
        EIS_tmp.raw['significance'] = data['Significance'].to_numpy()
        EIS_tmp.info = metadata
        EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, EIS_tmp.parameter['Sample'])


def load_parameters(sender, app_data, config, EIS):


def process_data(sender, app_data, config, EIS):