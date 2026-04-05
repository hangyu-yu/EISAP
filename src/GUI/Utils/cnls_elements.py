import os
import copy
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils


_PARAM_LIST = {
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
    'Warburg': ([1], [np.inf], [1e-10]),
    'RandleC': ([1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf], [1e-10, 1e-10, 1e-10, 1e-10]),
    'RandleCfFLW': ([1, 1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf, 1], [1e-10, 1e-10, 1e-10, 1e-10, 0.4]),
    'RandleCPE': ([1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf], [1e-10, 1e-10, 0.4, 1e-10, 1e-10]),
    'RandleCPEfFLW': ([1, 1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf, 1], [1e-10, 1e-10, 0.4, 1e-10, 1e-10, 0.4]),
}


def _sync_element_field_to_selected_files(config, element_index, field_name, param_index, new_value):
    """Propagate one edited value to all selected files using direct assignment."""
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        config.store[file_name_no_ext]['CNLS'].Elements[element_index][field_name][param_index] = new_value

def _element_table_change_callback(sender, app_data, config, element, _PARAM_RULES):
    """Callback function for element type change in the table.
    
    Args:
        sender: The sender of the callback.
        app_data: The data associated with the callback.
        config: Configuration object.
    """
    # Get the selected element type
    element_nbr = element['name'][-1]
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
    elif app_data == "Warburg":
        name_short = "W"
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
        # Disable RC initialization when Randle elements are present
        if dpg.does_item_exist("check_box_cnls_rc_initialization"):
            dpg.configure_item("check_box_cnls_rc_initialization", default_value=False, enabled=False)
            config.store['RC_fit_switch'] = False
    else:
        dpg.configure_item("checkbox_cnls_segement_constraints", enabled = True, default_value = True)
        config.store["segment_constraints"] = 'segment'
        # Enable RC initialization when no Randle elements
        if dpg.does_item_exist("check_box_cnls_rc_initialization"):
            dpg.configure_item("check_box_cnls_rc_initialization", enabled=True)
        
    # Rebuild the full table to keep all columns aligned after edits.
    update_elements(config)
    # Sync type/name change to all selected files.
    # Each file keeps its own Param values (preserve fitted/user results).
    # For new param indices (if count increased), extend with default 1.
    # Ub/Lb: preserve existing per-file values; extend new indices with displayed-file defaults.
    _idx = int(element_nbr) - 1
    _full_param_count = len(element['Param'])
    _default_ub = element['Ub']   # full list after build_element_table
    _default_lb = element['Lb']   # full list after build_element_table
    for _fn in config.selected_files:
        if _fn == config.display_file:
            continue
        _fk = os.path.splitext(_fn)[0]
        if _fk in config.store and 'CNLS' in config.store[_fk]:
            _elems = config.store[_fk]['CNLS'].Elements
            if isinstance(_elems, list) and len(_elems) > _idx:
                _old = _elems[_idx]
                _op = _old.get('Param', [])
                _ou = _old.get('Ub', [])
                _ol = _old.get('Lb', [])
                _elems[_idx] = {
                    'name': element['name'],
                    'type': app_data,
                    'Param': [(_op[i] if i < len(_op) else 1)             for i in range(_full_param_count)],
                    'Ub':    [(_ou[i] if i < len(_ou) else _default_ub[i]) for i in range(_full_param_count)],
                    'Lb':    [(_ol[i] if i < len(_ol) else _default_lb[i]) for i in range(_full_param_count)],
                }
    menu_remove_elements(config)
    if hasattr(gui_utils, "cnls_functions") and hasattr(gui_utils.cnls_functions, "refresh_selector_preview"):
        gui_utils.cnls_functions.refresh_selector_preview(config)

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
    element_idx = int(element['name'][-1])-1
    config.store["Elements"][element_idx]['Param'][i] = app_data

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
    element_idx = int(element['name'][-1])-1
    config.store["Elements"][element_idx]['Ub'][i] = app_data
    _sync_element_field_to_selected_files(config, element_idx, 'Ub', i, app_data)

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
    element_idx = int(element['name'][-1])-1
    config.store["Elements"][element_idx]['Lb'][i] = app_data
    _sync_element_field_to_selected_files(config, element_idx, 'Lb', i, app_data)

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
        'RandleCPE': [('Q0', 1), ('Alpha_Q0', 2), ('R_W0', 3), ('Tau_W0', 4),],
        'RandleCPEfFLW': [('Q0', 1), ('Alpha_Q0', 2), ('R_W0', 3), ('Tau_W0', 4), ('Alpha_W0', 5)],
        'Warburg': []  # no extra rows; only sigma (no tau — not subject to segment constraint)
    }
    parent_table = "Table_cnls_elements"
    rules = _PARAM_RULES.get(element['type'], [])
    with dpg.table_row(parent=parent_table):
        dpg.add_text(gui_utils.small_functions.string_abbreviation(element['name'], 2, 3))
        
        dpg.add_combo(
            items=list(config.store['element_list']),
            default_value=element['type'],
            width=-1,
            callback=lambda s, a: _element_table_change_callback(s, a, config, element, _PARAM_RULES),
        )
        dpg.add_text(config.store['element_list'][element['type']][0]+'0' if element['type'] in ['Inductor', 'Inductor_a', 'CPE', 'Capacitor', 'Warburg'] else 'R0')
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
    
    # Create the main element table header
    with dpg.table(
        parent="child_window_cnls_elements",
        tag = "Table_cnls_elements",
        header_row = True,
        borders_innerV=False,
        borders_innerH=False,
        borders_outerV=False,
        borders_outerH=False,
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
    element_type = dpg.get_item_label(sender)[4:]
    add_element_by_type(config, element_type)


def add_element_by_type(config, element_type):
    """Add a CNLS element directly by element type."""
    if element_type not in _PARAM_LIST:
        raise ValueError(f"Unsupported element type: {element_type}")

    param, ub, lb = _PARAM_LIST[element_type]
    # Get the number of existing elements
    element_nbr = len(config.store["Elements"]) + 1
    # Create a new element with default values
    new_element = {
        'name': f"{config.store['element_list'][element_type]}{element_nbr}",
        'type': element_type,
        'Param': copy.deepcopy(param),
        'Ub': copy.deepcopy(ub),
        'Lb': copy.deepcopy(lb)
    }
    config.store["Elements"].append(new_element)
    # Sync new element to all selected files
    for _fn in config.selected_files:
        _fk = os.path.splitext(_fn)[0]
        if _fk in config.store and 'CNLS' in config.store[_fk]:
            _elems = config.store[_fk]['CNLS'].Elements
            if isinstance(_elems, list) and len(_elems) < element_nbr:
                _elems.append(copy.deepcopy(new_element))
    build_element_table(config, new_element, element_nbr-1)
    menu_remove_elements(config)
    
    # Check if Randle element was added and update RC initialization checkbox
    type_list = [element['type'] for element in config.store["Elements"]]
    if any('Randle' in s for s in type_list):
        if dpg.does_item_exist("check_box_cnls_rc_initialization"):
            dpg.configure_item("check_box_cnls_rc_initialization", default_value=False, enabled=False)
            config.store['RC_fit_switch'] = False

    if hasattr(gui_utils, "cnls_functions") and hasattr(gui_utils.cnls_functions, "refresh_selector_preview"):
        gui_utils.cnls_functions.refresh_selector_preview(config)

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
    remove_element_by_name(config, name_to_remove)


def remove_element_by_name(config, name_to_remove):
    """Remove one CNLS element by its current name."""
    names = [elem['name'] for elem in config.store['Elements'][:]]
    if name_to_remove not in names:
        return False
    idx_to_remove = names.index(name_to_remove)
    config.store["Elements"].remove(config.store["Elements"][idx_to_remove])
    for i in range(len(config.store["Elements"])):
        config.store["Elements"][i]['name'] = f"{config.store['element_list'][config.store['Elements'][i]['type']]}{i+1}"
    # Sync removal to all selected files (per-file; preserve each file's own Param/Ub/Lb)
    for _fn in config.selected_files:
        if _fn == config.display_file:
            continue
        _fk = os.path.splitext(_fn)[0]
        if _fk in config.store and 'CNLS' in config.store[_fk]:
            _elems = config.store[_fk]['CNLS'].Elements
            if isinstance(_elems, list) and len(_elems) > idx_to_remove:
                del _elems[idx_to_remove]
                for _i in range(len(_elems)):
                    _elems[_i]['name'] = f"{config.store['element_list'][_elems[_i]['type']]}{_i+1}"
    update_elements(config)
    
    # Check if Randle elements still exist and update RC initialization checkbox
    type_list = [element['type'] for element in config.store["Elements"]]
    if any('Randle' in s for s in type_list):
        if dpg.does_item_exist("check_box_cnls_rc_initialization"):
            dpg.configure_item("check_box_cnls_rc_initialization", default_value=False, enabled=False)
            config.store['RC_fit_switch'] = False
    else:
        # Re-enable RC initialization if no Randle elements remain
        if dpg.does_item_exist("check_box_cnls_rc_initialization"):
            dpg.configure_item("check_box_cnls_rc_initialization", enabled=True)

    if hasattr(gui_utils, "cnls_functions") and hasattr(gui_utils.cnls_functions, "refresh_selector_preview"):
        gui_utils.cnls_functions.refresh_selector_preview(config)
    return True
