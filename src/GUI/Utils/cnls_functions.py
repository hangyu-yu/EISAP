import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
from src.Methods.CNLS.Circuit import Circuit

def _file_existence_check(config):
    """Check if the file exists in the store and contains valid CNLS data.
    
    Args:
        config: Configuration object containing store and display_file.
        
    Returns:
        bool: Whether the file exists and the data is valid.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    return (file_name_no_ext in config.store and 
            config.store[file_name_no_ext] is not None and 
            config.store[file_name_no_ext].get('CNLS') is not None and 
            config.store[file_name_no_ext]['CNLS'].f_fixed is not None)

def _update_peak_fixed(sender, app_data, i, config):
    print("-- Updating peak fixed frequency...")
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    if app_data == 0:
        config.store["peak_fixed_frequencies"] = []
        for j in range(dpg.get_value("input_nbr_peaks")):
            if _file_existence_check(config) and j <= len(config.store[file_name_no_ext]['CNLS'].f_fixed)-1:
                config.store["peak_fixed_frequencies"].append(config.store[file_name_no_ext]['CNLS'].f_fixed[j])
            else:
                config.store["peak_fixed_frequencies"].append(10**(dpg.get_value("input_nbr_peaks")-j-2))
        print("---- Peak fixed frequencies updated.")
    else:
        config.store["peak_fixed_frequencies"][i] = app_data
        print(f"---- Peak fixed frequency {i} updated to {app_data}.")

    try:
        config.store[file_name_no_ext]['CNLS'].f_fixed = config.store["peak_fixed_frequencies"]
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")

def dynamic_peak_ids(sender, appdata, config):
    """Dynamically generate peak frequency input columns.
    
    Args:
        config: Configuration object.
    """
    nbr_peaks = dpg.get_value("input_nbr_peaks")
    enable_state = (dpg.get_value("combo_peak_ID") == "fixed")
    _update_peak_fixed(None, 0, 0, config)
    if 'nbr_peaks' in config.store.keys():
        for i in range(config.store['nbr_peaks']):
            dpg.delete_item(f"table_row_peak_{i}")
        
    # Generate table rows
    for i in range(nbr_peaks):
        existing_rows = [item for item in dpg.get_item_children("Table_cnls_parameters", 1) 
                 if dpg.get_item_label(item).startswith("table_row_peak_")]
        for j in range(len(existing_rows)):
            if dpg.does_item_exist(f"table_row_peak_{j}"):
                dpg.delete_item(f"table_row_peak_{j}")
        # Set column headers
        if i == 0:
            label = "High f [Hz]"
        elif i == nbr_peaks-1:
            label = "Low f [Hz]"
        else:
            label = ""
        
        # Set default values (default values with exponential spacing)
        
        with dpg.table_row(parent="Table_cnls_parameters", tag=f"table_row_peak_{i}"):
            dpg.add_text(label)
            dpg.add_input_float(
                tag=f"input_peak_{i}",
                format="%.3f",
                enabled=enable_state,
                default_value=config.store["peak_fixed_frequencies"][i] if i <= len(config.store["peak_fixed_frequencies"])-1 else 10**(nbr_peaks-i-2),
                width=-1,
                step=0,
                step_fast=0,
                min_value=1e-100,
                max_value=1e100,
                callback=lambda s, a, idx=i: _update_peak_fixed(s, a, idx, config)
            )
    config.store['nbr_peaks'] = nbr_peaks

def peak_mode(sender, appdata, config):
    """Callback function for peak ID selection.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    if appdata == "fixed":
        dpg.configure_item("input_nbr_peaks", enabled=True)
    else:
        dpg.configure_item("input_nbr_peaks", enabled=False)
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    config.store[file_name_no_ext]['CNLS'].f_mode = appdata
    dynamic_peak_ids(sender, appdata, config)

def update_data_type(sender, appdata, config):
    """Update the data type for CNLS fitting.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    try:
        config.store[file_name_no_ext]['CNLS'].data_type = appdata
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")
    
    print(f"---- Data type updated to {appdata}.")

def nbr_iteration(sender, appdata, config):
    """Update the number of iterations for CNLS fitting.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    try:
        config.store[file_name_no_ext]['CNLS'].iteration = appdata
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")
    
    print(f"---- Number of iterations updated to {appdata}.")

def segment_constraints(sender, appdata, config):
    """Update the segment constraints for CNLS fitting.
    """
    if appdata:
        config.store["segment_constraints"] = 'segment'
    else:
        config.store["segment_constraints"] = 'free'
    print(f"---- Segment constraints updated to {config.store["segment_constraints"]}.")

# Update the element tables
def initialize_elements(config):
    """Update the initial elements for CNLS fitting.
    
    Args:
        config: Configuration object.
    """
    print("-- Initializing CNLS elements...")
    try:
        file_name_no_ext = os.path.splitext(config.display_file)[0]
        config.store['elements'] = config.store[file_name_no_ext]['CNLS'].Elements
        gui_utils.cnls_elements.initialize_element(config)
        print(f"---- CNLS elements initialization finished.")
    except:
        print("---- No previous CNLS elements found.")
    
# Initialize the CNLS element parameters
def initialize_parameters(sender, appdata, config):
    """Initialize the CNLS element parameters.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    print("-- Initializing CNLS parameters...")
    names = [elem['name'] for elem in config.store['Elements'][:]]
    has_randle = any('Randle' in name for name in names)
    if has_randle:
        dpg.configure_item("checkbox_cnls_segement_constraints", default_value=False, enabled=False)
        config.store["segment_constraints"] = 'free'
        print('---- Segment constraints set to free due to the presence of Randle elements.')
    
    # Load all the parameters from the CNLS setup
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            config.store[file_name_no_ext]['CNLS'] = Circuit(
                file_folder=config.folder_path, 
                filename=file_name, 
                Elements = config.store['Elements'], 
                EIS = EIS_tmp, 
                data_type = dpg.get_value('combo_cnls_data_type'))

            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            CNLS_tmp.iteration = dpg.get_value('input_nbr_iters')
            CNLS_tmp.f_fixed = config.store["peak_fixed_frequencies"]
            CNLS_tmp.f_mode = dpg.get_value("combo_peak_ID")
            CNLS_tmp.constraint_type = config.store["segment_constraints"]
            
            R_est, freq_est, alpha_est, nbr_peaks, tau_est = CNLS_tmp.PeakDerivative(CNLS_tmp.f_mode, f_fixed=CNLS_tmp.f_fixed, nbr_peaks_fixed=len(CNLS_tmp.f_fixed))
            R_est = R_est*EIS_tmp['tknv_' + CNLS_tmp.data_type.replace('_KK', '').replace('_DRT', '')]['RL']['Rp_ReIm']/np.sum(R_est)
            param_list = list(zip(R_est, tau_est, alpha_est))
            param_list = [[float(x) for x in tup] for tup in param_list]
            
            # try:
            for idx, element in enumerate(CNLS_tmp.Elements):
                if element['name'] == 'L1':
                    CNLS_tmp.Elements[0]['Param'] = [float(EIS_tmp['tknv_' + CNLS_tmp.data_type.replace('_KK', '').replace('_DRT', '')]['RL']['L_ReIm'])]
                elif element['name'] == 'R2':
                    CNLS_tmp.Elements[1]['Param'] = [float(EIS_tmp['tknv_' + CNLS_tmp.data_type.replace('_KK', '').replace('_DRT', '')]['RL']['Rs_ReIm'])]
                elif element['type'] not in ['Capacitor', 'CPE'] and not 'Randle' in element['name']:
                    CNLS_tmp.Elements[idx]['Param'] = param_list[0][:len(CNLS_tmp.Elements[idx]['Param'])]
                    param_list.remove(param_list[0])
                elif 'Randle' in element['name']:
                    if element['type'] == 'RandleC':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][2:] = param_list[0][:2]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCPE':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        CNLS_tmp.Elements[idx]['Param'][2] = param_list[0][2]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][3:] = param_list[0][:2]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCPEfFLW':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        CNLS_tmp.Elements[idx]['Param'][2] = param_list[0][2]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][3:] = param_list[0][:3]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCfFLW':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][2:] = param_list[0][:3]
                        param_list.remove(param_list[0])
                else:
                    raise ValueError(f"SOCEIS now does not support with {element['type']} for automatic initialization, please use the maunal mode")
            # except:
            #     raise ValueError("The number of initial guess does not match the number of elements.")
                
            if len(param_list) != 0:
                raise ValueError("The number of initial guess is more than the number of elements.")
            
            CNLS_tmp.initialize_elements()
            print(f"---- CNLS parameters initialized for {file_name}.")
    config.store["Elements"] = config.store[os.path.splitext(config.display_file)[0]]['CNLS'].Elements
    gui_utils.cnls_elements.update_elements(config)

# Run the CNLS fitting
def cnls_fit(sender, appdata, config):
    print(f"---- CNLS fit onging...")
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
        else:
            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            CNLS_tmp.Elements = config.store['Elements']
            for i in range(0, CNLS_tmp.iteration):
                CNLS_tmp.FitCircuit()
            CNLS_tmp.EvaluateCircuitDRT()
            gui_utils.cnls_table.table_update(config)
            