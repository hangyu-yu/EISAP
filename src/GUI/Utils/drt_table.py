import os
import math
import dearpygui.dearpygui as dpg

def table_update(config):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    with dpg.theme() as table_theme:
        # Header style (underline + background color)
        with dpg.theme_component(dpg.mvTable):
            # Header underline
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 5, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (70, 70, 70))  # Header background color
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (100, 100, 100))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (50, 50, 50))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))  # Header text color

        # Alternating row colors
        with dpg.theme_component(dpg.mvTableRow):
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (40, 40, 40))         # Odd rows
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (60, 60, 60))      # Even rows
        
        # Center-align text in table cells
        with dpg.theme_component(dpg.mvTable):
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 10, 10)  # Adjust padding for centering
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)    # Remove extra spacing
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)   # Adjust frame padding
    print("-- DRT data table updating...")
    for data_type in ["truncated", "smooth", "LCcorrect",  "extrapolation", "Resistance_truncated"]:
        dpg.delete_item(f"tab_drt_{data_type}_data")
        with dpg.tab(label=data_type[0].upper()+data_type[1:], tag=f"tab_drt_{data_type}_data", parent="tab_bar_drt_data"):
            dpg.delete_item(f"tab_bar_drt_{data_type}_data")
            with dpg.tab_bar(label=data_type[0].upper()+data_type[1:], tag=f"tab_bar_drt_{data_type}_data", parent=f"tab_drt_{data_type}_data"):
                if data_type != "Resistance_truncated":
                    for data_category in ["ReIm", "Re", "Im"]:
                        dpg.delete_item(f"tab_drt_{data_type}_{data_category}_data")
                        with dpg.tab(label=f"{data_type[0].upper()+data_type[1:]}_{data_category}", tag=f"tab_drt_{data_type}_{data_category}_data", parent=f"tab_bar_drt_{data_type}_data"):
                            if config.display_file != [] and config.display_file is not None:
                                # Clear existing table rows
                                dpg.delete_item(f"tab_drt_{data_type}_{data_category}_data_table")

                                # Reconstruct the table with new data
                                with dpg.table(
                                    parent=f"tab_drt_{data_type}_{data_category}_data",
                                    tag=f"tab_drt_{data_type}_{data_category}_data_table",
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
                                    if data_category != "Resistance":
                                        dpg.add_table_column(label="ID", width_fixed=True)
                                        dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                                        dpg.add_table_column(label="g [Ohm·s·cm2]", width_stretch=True)
                                        dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                                        dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)
                                        if config.display_file is not None and config.display_file != []:
                                            data = config.store[os.path.splitext(config.display_file)[0]]['EIS']
                                            if os.path.splitext(config.display_file)[0] in config.store.keys() and data[f"tknv_{data_type}"]:
                                                for idx in range(len(data[f"tknv_{data_type}"][data_category]['f'])):
                                                    with dpg.table_row():
                                                        dpg.add_text(f"{idx + 1}")
                                                        dpg.add_text(f"{data[f"tknv_{data_type}"][data_category]['f'][idx]:.2f}")
                                                        dpg.add_text(f"{data[f"tknv_{data_type}"][data_category]['g'][idx]:.6f}")
                                                        dpg.add_text(f"{data[f"tknv_{data_type}"][data_category]['Re'][idx]:.6f}")
                                                        dpg.add_text(f"{data[f"tknv_{data_type}"][data_category]['Im'][idx]:.6f}")
                                    else:
                                        if config.display_file is not None and config.display_file != []:
                                            data = config.store[os.path.splitext(config.display_file)[0]]['EIS']
                                            if os.path.splitext(config.display_file)[0] in config.store.keys() and data[f"tknv_{data_type}"]:
                                                dpg.add_table_column(label="Fitted resistances", width_stretch=True)
                                                dpg.add_table_column(label="Resistance values [Ohm·cm2]", width_stretch=True)
                                                for item in ["L-Re", "Rohm-Re", "Rpol-Re", "L-Im", "Rohm-Im", "Rpol-Im","L-ReIm", "Rohm-ReIm", "Rpol-ReIm"]:
                                                    item_idx = item.replace("-", "_").replace("ohm", "s").replace("pol", "p")
                                                    with dpg.table_row():
                                                        dpg.add_text(item)
                                                        dpg.add_text(f"{float(data[f"tknv_{data_type}"]['RL'][item_idx]):.6f}")
                                    if dpg.does_item_exist(f"tab_drt_{data_category}_data_table"):    
                                        dpg.bind_item_theme(f"tab_drt_{data_type}_{data_category}_data_table", table_theme)
                            else:
                                pass
                else:
                    dpg.delete_item(f"tab_drt_{data_type}_data")
                    with dpg.tab(label=f"{data_type}", tag=f"tab_drt_{data_type}_data", parent="tab_bar_drt_data"):
                        if config.display_file != [] and config.display_file is not None:
                            # Clear existing table rows
                            dpg.delete_item(f"tab_drt_{data_type}_data_table")

                            # Reconstruct the table with new data
                            with dpg.table(
                                parent=f"tab_drt_{data_type}_data",
                                tag=f"tab_drt_{data_type}_data_table",
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
                                dpg.add_table_column(label="File name", width_fixed=True)
                                dpg.add_table_column(label="L-ReIm [H·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Rohm-ReIm [Ohm·cm2]", width_stretch=True)
                                dpg.add_table_column(label="Rpol-ReIm [Ohm·cm2]", width_stretch=True)
                                
                                if config.display_file is not None and config.display_file != []:
                                    if os.path.splitext(config.display_file)[0] in config.store.keys() and config.store[os.path.splitext(config.display_file)[0]]['EIS'][f"tknv_truncated"]:
                                        for file_name in config.selected_files:
                                            file_name_no_ext = os.path.splitext(file_name)[0]
                                            EIS_tmp = config.store[file_name_no_ext]['EIS']
                                            with dpg.table_row():
                                                dpg.add_text(f"{file_name_no_ext[:15]}...{file_name_no_ext[-15:]}" if len(file_name_no_ext) > 30 else file_name_no_ext)
                                                dpg.add_text(f"{float(EIS_tmp.tknv_truncated['RL']['L_ReIm']):.6f}" if EIS_tmp.tknv_truncated['RL']['L_ReIm'] is not None else "N/A")
                                                dpg.add_text(f"{float(EIS_tmp.tknv_truncated['RL']['Rs_ReIm']):.6f}" if EIS_tmp.tknv_truncated['RL']['Rs_ReIm'] is not None else "N/A")
                                                dpg.add_text(f"{float(EIS_tmp.tknv_truncated['RL']['Rp_ReIm']):.6f}" if EIS_tmp.tknv_truncated['RL']['Rp_ReIm'] is not None else "N/A")
                                if dpg.does_item_exist(f"tab_drt_{data_type}_data_table"):
                                    dpg.bind_item_theme(f"tab_drt_{data_type}_data_table", table_theme)
                        else:
                            pass
    if config.display_file != [] and config.display_file is not None:
        print(f"---- EIS data table updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'drt_table.py' file.")