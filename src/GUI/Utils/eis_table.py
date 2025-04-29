import os
import math
import dearpygui.dearpygui as dpg

def table_update(config, table_theme):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    for idx, data_category in enumerate(["KK_data", "raw", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
        if config.display_file != []:
            print("-- Updating table:", data_category)
            # Clear existing table rows
            dpg.delete_item(f"tab_eis_{data_category}_data_table")

            # Reconstruct the table with new data
            with dpg.table(
                parent=f"tab_eis_{data_category}_data",
                tag=f"tab_eis_{data_category}_data_table",
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
                if data_category != "KK_data":
                    dpg.add_table_column(label="ID", width_fixed=True)
                    dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                    dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                    dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)
                    dpg.add_table_column(label="Z [Ohm·cm2]", width_stretch=True)
                    dpg.add_table_column(label="Phase [deg]", width_stretch=True)
                    if os.path.splitext(config.display_file)[0] in config.store.keys():
                        data = config.store[os.path.splitext(config.display_file)[0]]['EIS'][data_category]
                        for idx in range(len(data['f'])):
                            with dpg.table_row():
                                phase = math.degrees(math.atan2(data['Im'][idx], data['Re'][idx]))
                                dpg.add_text(f"{idx + 1}")
                                dpg.add_text(f"{data['f'][idx]:.2f}")
                                dpg.add_text(f"{data['Re'][idx]:.6f}")
                                dpg.add_text(f"{data['Im'][idx]:.6f}")
                                dpg.add_text(f"{data['Z'][idx]:.4f}")
                                dpg.add_text(f"{phase:.2f}")
                else:
                    dpg.add_table_column(label="ID", width_fixed=True)
                    dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                    dpg.add_table_column(label="Re residual [%]", width_stretch=True)
                    dpg.add_table_column(label="Im residual [%]", width_stretch=True)
                    if os.path.splitext(config.display_file)[0] in config.store.keys():
                        data = config.store[os.path.splitext(config.display_file)[0]]['EIS'].KK_data
                        for idx in range(len(data['f'])):
                            with dpg.table_row():
                                dpg.add_text(f"{idx + 1}")
                                dpg.add_text(f"{data['f'][idx]:.2f}")
                                dpg.add_text(f"{data['delta_Re_kk'][idx]:.6f}")
                                dpg.add_text(f"{data['delta_Im_kk'][idx]:.6f}")
                dpg.bind_item_theme(f"tab_eis_{data_category}_data_table", table_theme)
        
            print(f"---- Table {data_category} updated successfully.")

        else:
            print("---- Continue. The specified file does not exist, check 'eis_table.py' file.")
            pass