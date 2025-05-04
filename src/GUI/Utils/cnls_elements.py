import numpy as np
import dearpygui.dearpygui as dpg

# In-module functions
def _table_setup(element):
    if not dpg.does_item_exist(f"table_cnls_elements_{element['name'][-1]}"):
        dpg.add_table(
            parent= "child_window_cnls_elements",
            tag = f"table_cnls_elements_{element['name'][-1]}",
            header_row=False,
            borders_innerH=False,
            row_background=False,
            borders_outerH=False,
            policy=dpg.mvTable_SizingStretchSame
        )

def _column_setup(config, element):
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_name"), parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_type"), parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_param"), parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_value"), parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_ub"), parent=f"table_cnls_elements_{element['name'][-1]}")
    dpg.add_table_column(width_fixed=dpg.get_item_width("table_column_lb"), parent=f"table_cnls_elements_{element['name'][-1]}")

def _element_table_change_callback(sender, app_data, config, element):
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
    element['name'] = f"{name_short}{element_nbr}"
    element['type'] = app_data
    config.store['CNLS'].Elements[element_nbr]['name'] = element['name']
    config.store['CNLS'].Elements[element_nbr]['type'] = app_data
    func = config.store['element_function_map'][element['type']]
    func(config, element)

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
    config.store['CNLS'].Elements[element['name'][-1]]['Param'][i] = app_data

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
    config.store['CNLS'].Elements[element['name'][-1]]['Ub'][i] = app_data

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
    config.store['CNLS'].Elements[element['name'][-1]]['Lb'][i] = app_data

def _add_parameters_bounds(config, element, idx):
    dpg.add_input_float(default_value=element['Param'][idx] if element['Param'][idx] else 1, button=False, width=-1, callback=lambda s, a: _update_param_callback(s, a, config, element, 0))
    dpg.add_input_float(default_value=element['Ub'][idx] if element['Ub'][idx] else [], button=False, width=-1, callback=lambda s, a: _update_ub_callback(s, a, config, element, 0))
    dpg.add_input_float(default_value=element['Lb'][idx] if element['Ub'][idx] else [], button=False, width=-1, callback=lambda s, a: _update_lb_callback(s, a, config, element, 0))

# Functions for each element type
def build_element_table(config, element):
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
        dpg.add_text(element['name'], width=-1)
        dpg.add_combo(
            items=list(config.store['element_list']),
            default_value=element['type'],
            width=-1,
            callback=lambda s, a: _element_table_change_callback(s, a, config, element),
        )
        dpg.add_text(config.store['element_list'][element['type']][0]+'0' if element['type'] in ['Inductor', 'Inductor_a', 'CPE', 'Capacitor'] else 'R0')
        _add_parameters_bounds(config, element, 0)
    
    for title, param_idx in rules:
        with dpg.table_row(parent=parent_table):
            dpg.add_text("")
            dpg.add_text("")
            dpg.add_text(title)
            _add_parameters_bounds(config, element, param_idx)
            
# Main function to update the element table
def update_element(config):    
    if dpg.does_item_exist("Table_cnls_elements"):
        dpg.delete_item("Table_cnls_elements", children_only=True)
    with dpg.table(
        parent="child_window_cnls_elements",
        tag = "Table_cnls_elements",
        header_row = True,
        borders_innerV=True,  # Show vertical column lines
        borders_outerV=True,
        borders_outerH=True,
        row_background=True,  # Enable alternating row colors
        reorderable=True,     # Allow column reordering via drag-and-drop
        freeze_rows=1,        # Freeze header row (fixed during scrolling)
        scrollX=True,         # Enable horizontal scrolling
        scrollY=True,         # Enable vertical scrolling
        policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
    ):
        dpg.add_table_column(label="Name", width_stretch=True, tag="table_column_name")
        dpg.add_table_column(label="Type      ", width_stretch=True, tag="table_column_type")
        dpg.add_table_column(label="Param.", width_stretch=True, tag="table_column_param")
        dpg.add_table_column(label="Value", width_stretch=True, tag="table_column_value")
        dpg.add_table_column(label="Ub", width_stretch=True, tag="table_column_ub")
        dpg.add_table_column(label="Lb", width_stretch=True, tag="table_column_lb")
    
    for element in config.store['CNLS'].Elements:
        build_element_table(config, element)