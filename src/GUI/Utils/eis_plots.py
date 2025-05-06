import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def update_single_plots(config):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    print("-- EIS data single plots updating...")
    for idx, data_category in enumerate(["KK_data", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
        dpg.delete_item(f"tab_eis_{data_category}_plot_single")
        with dpg.tab(label=data_category, tag=f"tab_eis_{data_category}_plot_single", parent="tab_bar_eis_plot_single"):
            if config.display_file != [] and config.display_file is not None and os.path.splitext(config.display_file)[0] in config.store.keys() and 'EIS' in config.store[os.path.splitext(config.display_file)[0]] and config.store[os.path.splitext(config.display_file)[0]]['EIS'].KK_data['f'] is not None:
                # Clear existing plots
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_single_KK")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_single_Z_Phase")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_single_Re")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_single_Im")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_single_ReIM")

                data = config.store[os.path.splitext(config.display_file)[0]]['EIS']

                # Reconstruct the table with new data
                if data_category == "KK_data":
                    # Plot KK results
                    with dpg.plot(
                        # label="Karmar-Kronig results",
                        tag=f"tab_eis_{data_category}_data_plot_single_KK",
                        width = -1,
                        height=int(dpg.get_viewport_height() * 0.3),
                        no_menus=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, 
                        label="Residual [%]")
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Re_kk'], parent=y_axis, label="Re")
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Im_kk'], parent=y_axis, label="Im")
                        dpg.add_plot_legend()

                    # Plot impedance module
                    with dpg.plot(
                        # label="Raw impedance and phase",
                        tag=f"tab_eis_{data_category}_data_plot_single_Z_Phase",
                        width = -1,
                        height= -1,
                        no_menus=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis1 = dpg.add_plot_axis(dpg.mvYAxis, label="Z [Ohm·cm2]")
                        # dpg.set_axis_limits(y_axis1, 0, 1.1 * np.max(abs(data['raw']['Z'])))
                        dpg.add_scatter_series(data['raw']['f'], abs(data['raw']['Z']), parent=y_axis1, label="Z")

                        y_axis2 = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True)
                        # dpg.set_axis_limits(y_axis2, 0, 1.1 * np.max(-np.degrees(np.angle(data['raw']['Z']))))
                        dpg.add_scatter_series(data['raw']['f'], -np.degrees(np.angle(data['raw']['Z'])), parent=y_axis2, label="Phase")
                        dpg.add_plot_legend()
                else:
                    if data_category == "truncated":
                        compare_data = "raw"
                    else:
                        compare_data = "truncated"

                    # Bode plots
                    with dpg.plot(
                        # label = f"Real Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_single_Re",
                        width = -1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm·cm2]")
                        dpg.add_scatter_series(data[compare_data]['f'], data[compare_data]['Re'], parent=y_axis, label=compare_data.capitalize())
                        dpg.add_line_series(data[data_category]['f'], data[data_category]['Re'], parent=y_axis, label=data_category[0].upper() + data_category[1:])
                        dpg.add_plot_legend()

                    with dpg.plot(
                        # label = f"Imaginary Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_single_Im",
                        width = -1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]")
                        dpg.add_scatter_series(data[compare_data]['f'], -data[compare_data]['Im'], parent=y_axis, label=compare_data.capitalize())
                        dpg.add_line_series(data[data_category]['f'], -data[data_category]['Im'], parent=y_axis, label=data_category[0].upper() + data_category[1:])
                        dpg.add_plot_legend()
                    
                    # Nyquist plot
                    with dpg.plot(
                        # label = f"Nyquist - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_single_ReIM",
                        width = -1,
                        height= -1,
                        no_menus=True,
                        equal_aspects = True
                    ):
                        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm·cm2]")
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]")
                        dpg.add_scatter_series(data[compare_data]['Re'], -data[compare_data]['Im'], parent=y_axis, label=compare_data.capitalize())
                        dpg.add_line_series(data[data_category]['Re'], -data[data_category]['Im'], parent=y_axis, label=data_category[0].upper() + data_category[1:])
                        dpg.add_plot_legend()
            else:
                pass

    if config.display_file != [] and config.display_file is not None:
        print(f"---- EIS data single plots updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'eis_plots.py' file.")

def update_all_plots(config):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    print("-- EIS data all plots updating...")
    for idx, data_category in enumerate(["KK_data", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
        dpg.delete_item(f"tab_eis_{data_category}_plot_all")
        with dpg.tab(label=data_category, tag=f"tab_eis_{data_category}_plot_all", parent="tab_bar_eis_plot_all"):
            if config.display_file != [] and config.display_file is not None and os.path.splitext(config.display_file)[0] in config.store.keys() and 'EIS' in config.store[os.path.splitext(config.display_file)[0]] and config.store[os.path.splitext(config.display_file)[0]]['EIS'].KK_data['f'] is not None:
                # Clear existing table rows
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_all_KK")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_all_Z_Phase")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_all_Re")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_all_Im")
                dpg.delete_item(f"tab_eis_{data_category}_data_plot_all_ReIM")

                # Reconstruct the table with new data
                if data_category == "KK_data":
                    # Plot KK results
                    dpg.add_plot(
                        # label="Karmar-Kronig results",
                        tag=f"tab_eis_{data_category}_data_plot_all_KK",
                        width = -1,
                        height=int(dpg.get_viewport_height() * 0.3),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_eis_{data_category}_data_plot_all_KK")
                    y_axis_KK = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]", parent=f"tab_eis_{data_category}_data_plot_all_KK")

                    # Plot impedance module
                    dpg.add_plot(
                        # label="Raw impedance and phase",
                        tag=f"tab_eis_{data_category}_data_plot_all_Z_Phase",
                        width = -1,
                        height= -1,
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_eis_{data_category}_data_plot_all_Z_Phase")
                    y_axis1_Z_Phase = dpg.add_plot_axis(dpg.mvYAxis, label="Z [Ohm·cm2]", parent=f"tab_eis_{data_category}_data_plot_all_Z_Phase")
                    y_axis2_Z_Phase = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True, parent=f"tab_eis_{data_category}_data_plot_all_Z_Phase")

                    
                    for file_name in config.selected_files:
                        file_name_no_ext = os.path.splitext(file_name)[0]
                        data = config.store[file_name_no_ext]['EIS']
                        # KK results
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Re_kk'], parent=y_axis_KK, label=gui_utils.small_functions.string_abbreviation(f"Re-{file_name_no_ext}", 13, 12))
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Im_kk'], parent=y_axis_KK, label=gui_utils.small_functions.string_abbreviation(f"Im-{file_name_no_ext}", 13, 12))

                        # Impedance module and phase
                        dpg.add_scatter_series(data['raw']['f'], abs(data['raw']['Z']), parent=y_axis1_Z_Phase, label=gui_utils.small_functions.string_abbreviation(f"Z-{file_name_no_ext}", 12, 12))
                        dpg.add_scatter_series(data['raw']['f'], -np.degrees(np.angle(data['raw']['Z'])), parent=y_axis2_Z_Phase, label=gui_utils.small_functions.string_abbreviation(f"Phase-{file_name_no_ext}", 16, 12))

                    dpg.add_plot_legend(parent=f"tab_eis_{data_category}_data_plot_all_KK")
                    dpg.add_plot_legend(parent=f"tab_eis_{data_category}_data_plot_all_Z_Phase")
                else:
                    # Bode plots
                    dpg.add_plot(
                        # label = f"Real Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_all_Re",
                        width=-1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_eis_{data_category}_data_plot_all_Re")
                    y_axis_Re = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm·cm2]", parent=f"tab_eis_{data_category}_data_plot_all_Re")

                    dpg.add_plot(
                        # label = f"Imaginary Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_all_Im",
                        width=-1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_eis_{data_category}_data_plot_all_Im")
                    y_axis_Im = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]", parent=f"tab_eis_{data_category}_data_plot_all_Im")

                    # Nyquist plot
                    dpg.add_plot(
                        # label = f"Nyquist - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_eis_{data_category}_data_plot_all_ReIm",
                        width=-1,
                        height=-1,
                        no_menus=True,
                        equal_aspects = True
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm·cm2]", parent=f"tab_eis_{data_category}_data_plot_all_ReIm")
                    y_axis_Nyquist = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]", parent=f"tab_eis_{data_category}_data_plot_all_ReIm")
                    
                    for file_name in config.selected_files:
                        file_name_no_ext = os.path.splitext(file_name)[0]
                        data = config.store[file_name_no_ext]['EIS']
                        dpg.add_line_series(data[data_category]['f'], data[data_category]['Re'], parent=y_axis_Re, label=gui_utils.small_functions.string_abbreviation(f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}", 12, 12))

                        dpg.add_line_series(data[data_category]['f'], -data[data_category]['Im'], parent=y_axis_Im, label=gui_utils.small_functions.string_abbreviation(f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}", 12, 12))

                        dpg.add_line_series(data[data_category]['Re'], -data[data_category]['Im'], parent=y_axis_Nyquist, label=gui_utils.small_functions.string_abbreviation(f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}", 12, 12))

                    dpg.add_plot_legend(parent=f"tab_eis_{data_category}_data_plot_all_Re")
                    dpg.add_plot_legend(parent=f"tab_eis_{data_category}_data_plot_all_Im")
                    dpg.add_plot_legend(parent=f"tab_eis_{data_category}_data_plot_all_ReIm")
            else:
                pass

    if config.display_file != [] and config.display_file is not None:
        print(f"---- EIS data single plots updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'eis_plots.py' file.")