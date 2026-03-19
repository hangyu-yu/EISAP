import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utilis

def _smart_format(value):
    """
    Smartly format a value:
    - Use scientific notation if value is small (|value| < 0.001 and value != 0).
    - Otherwise, use standard floating-point format.
    - Handles numpy arrays, scalars, and empty inputs.
    """
    if isinstance(value, (np.ndarray, list)):
        if np.size(value) == 0:  # Check if array is empty
            return "%s"  # Return as string (e.g., "[]")
        else:
            # For arrays, format each element individually (not directly used here)
            return " ".join([_smart_format(v) for v in np.ravel(value)])
    elif isinstance(value, (float, int, np.float64, np.int64)):
        if value == 0:
            return "%.3f"  # Avoid scientific notation for zero
        elif abs(value) < 0.001:
            return "%.3e"  # Scientific notation (e.g., 1.234e-05)
        else:
            return "%.3f"  # Standard float (e.g., 0.1234)
    else:
        return "%s"  # Fallback for non-numeric types (e.g., strings)
def table_update(config):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    print("-- CNLS data table updating...")

    # Parameter results
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    print('-- Update CNLS parameter table...')
    dpg.delete_item("tab_cnls_data_parameters")
    with dpg.tab(label="Parameters", tag="tab_cnls_data_parameters", parent="tab_bar_cnls_data"):
        with dpg.table(
            parent=f"tab_cnls_data_parameters",
            tag=f"table_cnls_data_parameters",
            header_row=True,
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
            dpg.add_table_column(label="Variable", width_stretch=True)
            dpg.add_table_column(label="Value", width_stretch=True)
            dpg.add_table_column(label="UB", width_stretch=True)
            dpg.add_table_column(label="LB", width_stretch=True)
            dpg.add_table_column(label="Variance", width_stretch=True)
            dpg.add_table_column(label="Std. Error", width_stretch=True)
            dpg.add_table_column(label="pValue", width_stretch=True)
            try:
                CNLS_tmp = config.store[file_name_no_ext]['CNLS']
                if CNLS_tmp.ElementsParamNames == []:
                    if config.store["Elements"] is None:
                        config.store["Elements"] = [
                            {'name': 'L1', 'type': 'Inductor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
                            {'name': 'R2', 'type': 'Resistor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
                        ]
                    gui_utilis.cnls_elements.update_elements(config)
                else:
                    for idx, variable in enumerate(CNLS_tmp.ElementsParamNames):
                        with dpg.table_row():
                            dpg.add_text(variable)
                            param_value = CNLS_tmp.ElementsParamValues[idx]
                            ub_value = CNLS_tmp.UpperBound[idx]
                            lb_value = CNLS_tmp.LowerBound[idx]
                            dpg.add_text(_smart_format(param_value) % param_value)
                            dpg.add_text(_smart_format(ub_value) % ub_value)
                            dpg.add_text(_smart_format(lb_value) % lb_value)
                            dpg.add_text(_smart_format(CNLS_tmp.ElementsParamVariance[idx]) % CNLS_tmp.ElementsParamVariance[idx])
                            dpg.add_text(_smart_format(CNLS_tmp.ElementsParamStandardErrors[idx]) % CNLS_tmp.ElementsParamStandardErrors[idx])
                            dpg.add_text(_smart_format(CNLS_tmp.ElementsParamPValues[idx]) % CNLS_tmp.ElementsParamPValues[idx])
                print(f"---- CNLS data table updated successfully.")
            except:
                print("[Warning] CNLS data not available for the selected file, check cnls_table.py function.")
    
    # Impedance data
    try:
        print('-- Updating CNLS impedance data table...')
        if CNLS_tmp.Z is not None:
            Impedance_data_columns = CNLS_tmp.Z.columns.tolist()
            Impedance_data_columns.remove('Zmes') if 'Zmes' in Impedance_data_columns else None
            Impedance_data_columns.remove('Ztot0') if 'Ztot0' in Impedance_data_columns else None
            dpg.delete_item(f"tab_cnls_data_impedance")
            with dpg.tab(label="Impedance", tag="tab_cnls_data_impedance", parent="tab_bar_cnls_data"):
                with dpg.tab_bar(tag=f"tab_bar_impedance_data", parent="tab_cnls_data_impedance"):
                    for element in Impedance_data_columns:
                            dpg.add_tab(label=element, tag=f"tab_impedance_data_{element}", parent=f"tab_bar_impedance_data")
                            with dpg.table(
                                parent=f"tab_impedance_data_{element}",
                                tag=f"table_cnls_impedance_data_{element}",
                                header_row=True,
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
                                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                                dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Z [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Phase [deg]", width_stretch=True)
                                for idx in range(CNLS_tmp.Z.shape[0]):
                                    with dpg.table_row():
                                        dpg.add_text(str(CNLS_tmp.f[idx]))
                                        dpg.add_text(_smart_format(np.real(CNLS_tmp.Z[element][idx])) % np.real(CNLS_tmp.Z[element][idx]))
                                        dpg.add_text(_smart_format(np.imag(CNLS_tmp.Z[element][idx])) % np.imag(CNLS_tmp.Z[element][idx]))
                                        dpg.add_text(_smart_format(np.abs(CNLS_tmp.Z[element][idx])) % np.abs(CNLS_tmp.Z[element][idx]))
                                        dpg.add_text(_smart_format(np.angle(CNLS_tmp.Z[element][idx], deg=True)) % np.angle(CNLS_tmp.Z[element][idx], deg=True))
        print(f"---- CNLS impedance data table updated successfully.")
    except:
        print("[Warning] CNLS impedance data not available for the selected file, check cnls_table.py function.")

    # DRT data
    print('-- Updating CNLS DRT data table...')
    dpg.delete_item("tab_cnls_data_drt")
    with dpg.tab(label="DRT", tag="tab_cnls_data_drt", parent="tab_bar_cnls_data"):
        try:
            with dpg.table(
                parent=f"tab_cnls_data_drt",
                tag=f"table_cnls_data_drt",
                header_row=True,
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
                dpg.add_table_column(label="Frequency [Hz]", width_fixed=True)
                dpg.add_table_column(label="Origin", width_fixed=True)
                dpg.add_table_column(label="Total", width_fixed=True)
                if CNLS_tmp.Elements is not None:
                    for idx in range(len(CNLS_tmp.Elements)):
                        dpg.add_table_column(label=CNLS_tmp.Elements[idx]['name'], width_fixed=True)
                    
                    for idx in range(len(CNLS_tmp.f)):
                        with dpg.table_row():
                            # Frequency column (already a scalar)
                            freq = CNLS_tmp.f[idx]
                            dpg.add_text(str(freq))
                            
                            # DRTmes data (ensure scalar)
                            drt_mes = CNLS_tmp.DRTmes[idx]
                            dpg.add_text(_smart_format(drt_mes) % drt_mes)
                            
                            # DRT["ReIm"]["g"] data (ensure scalar)
                            drt_g = CNLS_tmp.DRT["ReIm"]["g"][idx]
                            dpg.add_text(_smart_format(drt_g) % drt_g)
                            
                            # Element-wise DRT data (ensure scalar)
                            for element in CNLS_tmp.Elements:
                                element_value = CNLS_tmp.ElementDRTs[element['name']]['ReIm']['g'][idx]
                                dpg.add_text(_smart_format(element_value) % element_value)
                print(f"---- CNLS DRT data table updated successfully.")
        except:
            print("[Warning] CNLS DRT data not available for the selected file, check cnls_table.py function.")

    if config.display_file != [] and config.display_file is not None:
        print(f"---- CNLS data table updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'cnls_table.py' file.")