import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

# In-module functions
def _table_setup(element):
    if not dpg.does_item_exist(f"table_cnls_elements_{element['name'][-1]}"):
        dpg.add_table(
            parent= "child_window_cnls_elements",
            tag = f"table_cnls_elements_{element['name'][-1]}",
            header_row=False,
            borders_innerH=False,
            row_background=False,
            borders_outerH=True,
            policy=dpg.mvTable_SizingStretchSame
        )

def _column_setup(config, element):
    viewport_width = dpg.get_viewport_width()
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_stretch=True, parent=f"table_cnls_elements_{element['name'][-1]}")

def _element_table_change_callback(sender, app_data, config, element, _PARAM_RULES):
    """Callback function for element type change in the table.
    
    Args:
        sender: The sender of the callback.
        app_data: The data associated with the callback.
        config: Configuration object.
    """
    # Get the selected element type
    element_nbr = element['name'][-1]
    dpg.delete_item(f"table_cnls_elements_{element_nbr}", children_only=True)
    element['type'] = app_data
    if app_data == "Resistor":
        name_short = "R"
    elif app_data == "Inductor":
        name_short = "L"
    elif app_data == "Inductor_a":
        name_short = "La"
    elif app_data == "Capacitor":
        name_short = "C"
    elif app_data == "CPE":
        name_short = "Q"
    else:
        name_short = app_data
    rules = _PARAM_RULES.get(element['type'], [])
    element['name'] = f"{name_short}{element_nbr}"
    element['type'] = app_data
    element['Param'] = [element['Param'][0]]
    element['Ub'] = [element['Ub'][0]]
    element['Lb'] = [element['Lb'][0]]
    config.store["Elements"][int(element_nbr)-1] = element
    type_list = [element['type'] for element in config.store["Elements"]]
    if any('Randle' in s for s in type_list):
        dpg.configure_item("checkbox_cnls_segement_constraints", enabled = False, default_value = False)
        config.store["segment_constraints"] = 'free'
    else:
        dpg.configure_item("checkbox_cnls_segement_constraints", enabled = True, default_value = True)
        config.store["segment_constraints"] = 'segment'
        
    build_element_table(config, element, int(element_nbr)-1)
    menu_remove_elements(config)

def _update_param_callback(sender, app_data, config, element, i):
    """Callback function for updating the parameter in the table.
    
    Args:
        sender: The sender of the callback.
        app_data: The data associated with the callback.
        config: Configuration object.
        element: The element being updated.
    """
    # Update the parameter value
    element['Param'][i] = app_data
    config.store["Elements"][int(element['name'][-1])-1]['Param'][i] = app_data

def _update_ub_callback(sender, app_data, config, element, i):
    """Callback function for updating the parameter in the table.
    
    Args:
        sender: The sender of the callback.
        app_data: The data associated with the callback.
        config: Configuration object.
        element: The element being updated.
    """
    # Update the parameter value
    element['Ub'][i] = app_data
    config.store["Elements"][int(element['name'][-1])-1]['Ub'][i] = app_data

def _update_lb_callback(sender, app_data, config, element, i):
    """Callback function for updating the parameter in the table.
    
    Args:
        sender: The sender of the callback.
        app_data: The data associated with the callback.
        config: Configuration object.
        element: The element being updated.
    """
    # Update the parameter value
    element['Lb'][i] = app_data
    config.store["Elements"][int(element['name'][-1])-1]['Lb'][i] = app_data

def _smart_format(value):
    """Smartly choose format: use scientific notation for values less than 0.001, otherwise use standard floating-point format."""
    if value != [] and abs(value) < 0.001 and value != 0 :
        return "%.2e"  # Scientific notation (e.g., 1.234e-05)
    else:
        return "%.3f"  # Standard floating-point format (e.g., 0.001)

def _add_parameters_bounds(config, element, idx, _PARAM_RULES, element_idx):
    param_name = None
    for rule in _PARAM_RULES.get(element['type'], []):
        if rule[1] == idx:  # Check if the parameter index matches
            param_name = rule[0]
            break
    # Set default values (if it's an Alpha parameter, set upper bound to 1 and lower bound to 0.4)
    default_value_param = element['Param'][idx] if (len(element['Param']) > idx and element['Param'][idx] is not None) else 1
    if param_name and "Alpha" in param_name:
        default_value_ub = element['Ub'][idx] if (len(element['Ub']) > idx and element['Ub'][idx] is not None) else 1.0
        default_value_lb = element['Lb'][idx] if (len(element['Lb']) > idx and element['Lb'][idx] is not None) else 0.4
    else:
        default_value_ub = element['Ub'][idx] if (len(element['Ub']) > idx and element['Ub'][idx] is not None) else np.inf
        default_value_lb = element['Lb'][idx] if (len(element['Lb']) > idx and element['Lb'][idx] is not None) else 1e-10
    

    dpg.add_input_float(default_value=default_value_param,
                        format=_smart_format(default_value_param),
                        step=0, 
                        step_fast=0, 
                        width=-1, 
                        callback=lambda s, a: _update_param_callback(s, a, config, element, 0))
    dpg.add_input_float(default_value=default_value_ub, 
                        format=_smart_format(default_value_ub), 
                        step=0, 
                        step_fast=0, 
                        width=-1, 
                        callback=lambda s, a: _update_ub_callback(s, a, config, element, idx))
    dpg.add_input_float(default_value=default_value_lb, 
                        format=_smart_format(default_value_lb), 
                        step=0, 
                        step_fast=0, 
                        width=-1, 
                        callback=lambda s, a: _update_lb_callback(s, a, config, element, idx))
                        
    if len(config.store["Elements"][element_idx]['Param'])-1 < idx:
        config.store["Elements"][element_idx]['Param'].append(default_value_param)
        config.store["Elements"][element_idx]['Ub'].append(default_value_ub)
        config.store["Elements"][element_idx]['Lb'].append(default_value_lb)
    else:
        config.store["Elements"][element_idx]['Param'][idx] = default_value_param
        config.store["Elements"][element_idx]['Ub'][idx] = default_value_ub
        config.store["Elements"][element_idx]['Lb'][idx] = default_value_lb

# Functions for each element type
def build_element_table(config, element, element_idx):
    _PARAM_RULES = {
        'CPE': [('Alpha0', 1)],
        'Inductor_a': [('Alpha0', 1)],
        'RC': [('Tau0', 1)],
        'RQ': [('Tau0', 1), ('Alpha0', 2)],
        'Gerisher': [('Tau0', 1)],
        'fFLW': [('Tau0', 1), ('Alpha0', 2)],
        'FLW': [('Tau0', 1)],
        'RandleC': [('C0', 1), ('R_W0', 2), ('Tau_W0', 3)],
        'RandleCfFLW': [('C0', 1), ('R_W0', 2), ('Tau_W0', 3), ('Alpha_W0', 4)],
        'RandleCPE': [('Q0', 1), ('Alpha_Q0', 2), ('R_W0', 3), ('Tau_W0', 4), ('Alpha_W0', 5)],
        'RandleCPEfFLW': [('Q0', 1), ('Alpha_Q0', 2), ('R_W0', 3), ('Tau_W0', 4), ('Alpha_W0', 5)]
    }
    parent_table = f"table_cnls_elements_{element['name'][-1]}"
    rules = _PARAM_RULES.get(element['type'], [])

    _table_setup(element)
    _column_setup(config, element)
    with dpg.table_row(parent=parent_table):
        dpg.add_text(gui_utils.small_functions.string_abbreviation(element['name'], 2, 3))
        dpg.add_combo(
            items=list(config.store['element_list']),
            default_value=element['type'],
            width=-1,
            callback=lambda s, a: _element_table_change_callback(s, a, config, element, _PARAM_RULES),
        )
        dpg.add_text(config.store['element_list'][element['type']][0]+'0' if element['type'] in ['Inductor', 'Inductor_a', 'CPE', 'Capacitor'] else 'R0')
        _add_parameters_bounds(config, element, 0, _PARAM_RULES, element_idx)
    
    for title, param_idx in rules:
        with dpg.table_row(parent=parent_table):
            dpg.add_text("")
            dpg.add_text("")
            dpg.add_text(title)
            _add_parameters_bounds(config, element, param_idx, _PARAM_RULES, element_idx)
            
# Main function to update the element table
def update_elements(config):
    dpg.delete_item("child_window_cnls_elements", children_only=True)
    # Create the new tables
    with dpg.table(
        parent="child_window_cnls_elements",
        tag = "Table_cnls_elements",
        header_row = True,
        borders_innerV=True,  # Show vertical column lines
        borders_outerV=True,
        borders_outerH=True,
        row_background=True,  # Enable alternating row colors
        freeze_rows=1,        # Freeze header row (fixed during scrolling)
        # scrollX=True,         # Enable horizontal scrolling
        # scrollY=True,         # Enable vertical scrolling
        # policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
    ):
        dpg.add_table_column(label="Name", width_stretch=True)
        dpg.add_table_column(label="Type", width_stretch=True)
        dpg.add_table_column(label="Param.", width_stretch=True)
        dpg.add_table_column(label="Value", width_stretch=True)
        dpg.add_table_column(label="Ub", width_stretch=True)
        dpg.add_table_column(label="Lb", width_stretch=True)
    # try:
    for element_idx, element in enumerate(config.store["Elements"]):
        build_element_table(config, element, element_idx)
    # except:
        # print("---- No emlements found.")
    menu_remove_elements(config)

def add_element(sender, appdata, config):
    """Add a new element to the CNLS fitting table.
    
    Args:
        sender: The sender of the callback.
        appdata: The data associated with the callback.
        config: Configuration object.
        element_type: The type of element to add.
    """
    # Initialize the element parameters
    element_type = dpg.get_item_label(sender)[4:]
    _PARAM_List = {
        'Inductor': ([1], [np.inf], [1e-10]),
        'Resistor': ([1], [np.inf], [1e-10]),
        'Capacitor': ([1], [np.inf], [1e-10]),
        'CPE': ([1, 1], [np.inf, 1], [1e-10, 0.4]),
        'Inductor_a': ([1, 1], [np.inf, 1], [1e-10, 0.4]),
        'RC': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
        'RQ': ([1, 1, 1], [np.inf, np.inf, 1], [1e-10, 1e-10, 0.4]),
        'Gerisher': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
        'fFLW': ([1, 1, 1], [np.inf, np.inf, 1], [1e-10, 1e-10, 0.4]),
        'FLW': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
        'RandleC': ([1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf], [1e-10, 1e-10, 1e-10, 1e-10]),
        'RandleCfFLW': ([1, 1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf, 1], [1e-10, 1e-10, 1e-10, 1e-10, 0.4]),
        'RandleCPE': ([1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf], [1e-10, 1e-10, 0.4, 1e-10, 1e-10]),
        'RandleCPEfFLW': ([1, 1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf, 1], [1e-10, 1e-10, 0.4, 1e-10, 1e-10, 0.4])
    }
    param, ub, lb = _PARAM_List[element_type]
    # Get the number of existing elements
    element_nbr = len(config.store["Elements"]) + 1
    # Create a new element with default values
    new_element = {
        'name': f"{config.store['element_list'][element_type]}{element_nbr}",
        'type': element_type,
        'Param': param,
        'Ub': ub,
        'Lb': lb
    }
    config.store["Elements"].append(new_element)
    build_element_table(config, new_element, element_nbr-1)
    menu_remove_elements(config)

def menu_remove_elements(config):
    """Create a menu for removing elements from the CNLS fitting table.
    
    Args:
        config: Configuration object.
    """
    if dpg.does_item_exist("menu_remove_elements"):
        dpg.delete_item("menu_remove_elements")
    with dpg.menu(label="Remove elements", parent="menu_cnls_parameters", tag="menu_remove_elements"):
        for name in [elem['name'] for elem in config.store['Elements'][:]]:
            dpg.add_menu_item(
                label=f"Remove {name}",
                callback=lambda s, a: remove_element(s, a, config)
            )

def remove_element(sender, appdata, config):
    """Remove an element from the CNLS fitting table.
    
    Args:
        sender: The sender of the callback.
        appdata: The data associated with the callback.
        config: Configuration object.
    """
    # Get the number of existing elements
    name_to_remove = dpg.get_item_label(sender)[7:]
    names = [elem['name'] for elem in config.store['Elements'][:]]
    idx_to_remove = names.index(name_to_remove)
    config.store["Elements"].remove(config.store["Elements"][idx_to_remove])
    for i in range(len(config.store["Elements"])):
        config.store["Elements"][i]['name'] = f"{config.store['element_list'][config.store['Elements'][i]['type']]}{i+1}"
    update_elements(config)
