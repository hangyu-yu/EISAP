import os
import numpy as np
import dearpygui.dearpygui as dpg

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
        for j in range(dpg.get_value("input_nbr_peaks")):
            if _file_existence_check(config) and j <= len(config.store[file_name_no_ext]['CNLS'].f_fixed)-1:
                config.store["peak_fixed_frequencies"][j] = config.store[file_name_no_ext]['CNLS'].f_fixed[j]
            else:
                config.store["peak_fixed_frequencies"] = [10**(dpg.get_value("input_nbr_peaks")-j-2) for j in range(dpg.get_value("input_nbr_peaks"))]
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
                format="%.2f",
                enabled=enable_state,
                default_value=config.store["peak_fixed_frequencies"][i],
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

def update_data_type(sender, appdata,config):
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