import os
import numpy as np
import dearpygui.dearpygui as dpg

def update_single_plots(config):
    """
    Update the table with the latest data from DRT and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    print("-- DRT data single plots updating...")
    for data_type in ["truncated", "smooth", "LCcorrect", "extrapolation", "EIS_truncated"]:
        dpg.delete_item(f"tab_drt_{data_type}_plot")
        with dpg.tab(label=data_type[0].upper()+data_type[1:], tag=f"tab_drt_{data_type}_plot_single", parent="tab_bar_drt_plot_single"):
            if data_type != "EIS_truncated":
                if config.display_file != [] and config.display_file is not None and os.path.splitext(config.display_file)[0] in config.store.keys():
                    # Clear existing plots
                    dpg.delete_item(f"tab_drt_{data_type}_data_plot_single")

                    data = config.store[os.path.splitext(config.display_file)[0]]['EIS']

                    # Plot DRT results
                    with dpg.plot(
                        # label="Karmar-Kronig results",
                        tag=f"tab_drt_{data_type}_data_plot_single",
                        width  = -1,
                        height = -1,
                        no_menus=True,
                    ):
                        if os.path.splitext(config.display_file)[0] in config.store.keys() and data[f"tknv_{data_type}"]:
                            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                            for data_category in ["ReIm", "Re", "Im"]:
                                dpg.set_axis_limits(y_axis, 0, np.max(data[f"tknv_{data_type}"][data_category]['g']) * 1.1)
                                dpg.add_line_series(data[f"tknv_{data_type}"][data_category]['f'], data[f"tknv_{data_type}"][data_category]['g'], parent=y_axis, label=data_category)
                            dpg.add_plot_legend()
                else:
                    pass
            else:
                dpg.delete_item(f"tab_bar_drt_{data_type}_plot_single")
                with dpg.tab_bar(label=data_type[0].upper()+data_type[1:], tag=f"tab_bar_drt_{data_type}_plot_single", parent=f"tab_drt_{data_type}_plot_single"):
                    dpg.delete_item(f"tab_drt_{data_type}_{data_category}_plot_single")
                    data = config.store[os.path.splitext(config.display_file)[0]]['EIS']
                    for data_category in ["ReIm", "Re", "Im"]:
                        with dpg.tab(label=data_category, tag=f"tab_drt_{data_type}_{data_category}_plot_single", parent=f"tab_bar_drt_{data_type}_plot_single"):
                            if config.display_file != [] and config.display_file is not None and os.path.splitext(config.display_file)[0] in config.store.keys():
                                # Bode plots
                                dpg.delete_item(f"tab_drt_{data_type}_{data_category}_data_plot_single_Re")
                                with dpg.plot(
                                    # label="Karmar-Kronig results",
                                    tag=f"tab_drt_{data_type}_{data_category}_data_plot_single_Re",
                                    width  = -1,
                                    height = int(dpg.get_viewport_height() * 0.25),
                                    no_menus=True,
                                ):
                                    if os.path.splitext(config.display_file)[0] in config.store.keys() and data.tknv_truncated:
                                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm·cm2]")
                                        dpg.add_scatter_series(data.truncated['f'], data.truncated['Re'], parent=y_axis, label=f"{data_category}_truncated")
                                        dpg.add_line_series(data.smooth['f'], data.smooth['Re'], parent=y_axis, label=f"{data_category}_truncated_KK_smooth")
                                        dpg.add_line_series(data.tknv_truncated[data_category]['f'], data.tknv_truncated[data_category]['Re'], parent=y_axis, label=f"{data_category}_truncated_DRT_smooth")
                                        dpg.add_plot_legend()

                                dpg.delete_item(f"tab_drt_{data_type}_{data_category}_data_plot_single_Im")
                                with dpg.plot(
                                    # label="Karmar-Kronig results",
                                    tag=f"tab_drt_{data_type}_{data_category}_data_plot_single_Im",
                                    width  = -1,
                                    height = int(dpg.get_viewport_height() * 0.25),
                                    no_menus=True,
                                ):
                                    if os.path.splitext(config.display_file)[0] in config.store.keys() and data.tknv_truncated:
                                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]")
                                        dpg.add_scatter_series(data.truncated['f'], -data.truncated['Im'], parent=y_axis, label=f"{data_category}_truncated")
                                        dpg.add_line_series(data.smooth['f'], -data.smooth['Im'], parent=y_axis, label=f"{data_category}_truncated_KK_smooth")
                                        dpg.add_line_series(data.tknv_truncated[data_category]['f'], -data.tknv_truncated[data_category]['Im'], parent=y_axis, label=f"{data_category}_truncated_DRT_smooth")
                                        dpg.add_plot_legend()

                                # Nyquist plot
                                dpg.delete_item(f"tab_drt_{data_type}_{data_category}_data_plot_single_ReIm")
                                with dpg.plot(
                                    # label="Karmar-Kronig results",
                                    tag=f"tab_drt_{data_type}_{data_category}_data_plot_single_ReIm",
                                    width  = -1,
                                    height = -1,
                                    no_menus=True,
                                ):
                                    if os.path.splitext(config.display_file)[0] in config.store.keys() and data.tknv_truncated:
                                        dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm·cm2]", log_scale=True)
                                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]")
                                        dpg.add_scatter_series(data.truncated['Re'], -data.truncated['Im'], parent=y_axis, label=f"{data_category}_truncated")
                                        dpg.add_line_series(data.smooth['Re'], -data.smooth['Im'], parent=y_axis, label=f"{data_category}_truncated_KK_smooth")
                                        dpg.add_line_series(data.tknv_truncated[data_category]['Re'], -data.tknv_truncated[data_category]['Im'], parent=y_axis, label=f"{data_category}_truncated_DRT_smooth")
                                        dpg.add_plot_legend()
                
    if config.display_file != [] and config.display_file is not None:
        print(f"---- DRT data single plots updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'drt_plots.py' file.")

def update_all_plots(config):
    """
    Update the table with the latest data from DRT and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    print("-- DRT data all plots updating...")
    for idx, data_category in enumerate(["KK_data", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
        dpg.delete_item(f"tab_drt_{data_category}_plot_all")
        with dpg.tab(label=data_category, tag=f"tab_drt_{data_category}_plot_all", parent="tab_bar_drt_plot_all"):
            if config.display_file != [] and config.display_file is not None and os.path.splitext(config.display_file)[0] in config.store.keys():
                # Clear existing table rows
                dpg.delete_item(f"tab_drt_{data_category}_data_plot_all_KK")
                dpg.delete_item(f"tab_drt_{data_category}_data_plot_all_Z_Phase")
                dpg.delete_item(f"tab_drt_{data_category}_data_plot_all_Re")
                dpg.delete_item(f"tab_drt_{data_category}_data_plot_all_Im")
                dpg.delete_item(f"tab_drt_{data_category}_data_plot_all_ReIM")

                # Reconstruct the table with new data
                if data_category == "KK_data":
                    # Plot KK results
                    dpg.add_plot(
                        # label="Karmar-Kronig results",
                        tag=f"tab_drt_{data_category}_data_plot_all_KK",
                        width = -1,
                        height=int(dpg.get_viewport_height() * 0.3),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_drt_{data_category}_data_plot_all_KK")
                    y_axis_KK = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]", parent=f"tab_drt_{data_category}_data_plot_all_KK")

                    # Plot impedance module
                    dpg.add_plot(
                        # label="Raw impedance and phase",
                        tag=f"tab_drt_{data_category}_data_plot_all_Z_Phase",
                        width = -1,
                        height= -1,
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_drt_{data_category}_data_plot_all_Z_Phase")
                    y_axis1_Z_Phase = dpg.add_plot_axis(dpg.mvYAxis, label="Z [Ohm·cm2]", parent=f"tab_drt_{data_category}_data_plot_all_Z_Phase")
                    y_axis2_Z_Phase = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True, parent=f"tab_drt_{data_category}_data_plot_all_Z_Phase")

                    
                    for file_name in config.selected_files:
                        file_name_no_ext = os.path.splitext(file_name)[0]
                        data = config.store[file_name_no_ext]['EIS']
                        # KK results
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Re_kk'], parent=y_axis_KK, label=f"Re-{file_name_no_ext}")
                        dpg.add_scatter_series(data['KK_data']['f'], data['KK_data']['delta_Im_kk'], parent=y_axis_KK, label=f"Im-{file_name_no_ext}")

                        # Impedance module and phase
                        dpg.add_scatter_series(data['raw']['f'], abs(data['raw']['Z']), parent=y_axis1_Z_Phase, label=f"Z-{file_name_no_ext}")
                        dpg.add_scatter_series(data['raw']['f'], -np.degrees(np.angle(data['raw']['Z'])), parent=y_axis2_Z_Phase, label=f"Phase-{file_name_no_ext}")

                    dpg.add_plot_legend(parent=f"tab_drt_{data_category}_data_plot_all_KK")
                    dpg.add_plot_legend(parent=f"tab_drt_{data_category}_data_plot_all_Z_Phase")
                else:
                    # Bode plots
                    dpg.add_plot(
                        # label = f"Real Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_drt_{data_category}_data_plot_all_Re",
                        width=-1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_drt_{data_category}_data_plot_all_Re")
                    y_axis_Re = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm·cm2]", parent=f"tab_drt_{data_category}_data_plot_all_Re")

                    dpg.add_plot(
                        # label = f"Imaginary Bode - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_drt_{data_category}_data_plot_all_Im",
                        width=-1,
                        height=int(dpg.get_viewport_height() * 0.25),
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True, parent=f"tab_drt_{data_category}_data_plot_all_Im")
                    y_axis_Im = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]", parent=f"tab_drt_{data_category}_data_plot_all_Im")

                    # Nyquist plot
                    dpg.add_plot(
                        # label = f"Nyquist - {data_category[0].upper() + data_category[1:]}",
                        tag=f"tab_drt_{data_category}_data_plot_all_ReIm",
                        width=-1,
                        height=-1,
                        no_menus=True,
                    )
                    dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm·cm2]", parent=f"tab_drt_{data_category}_data_plot_all_ReIm")
                    y_axis_Nyquist = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm·cm2]", parent=f"tab_drt_{data_category}_data_plot_all_ReIm")
                    
                    for file_name in config.selected_files:
                        file_name_no_ext = os.path.splitext(file_name)[0]
                        data = config.store[file_name_no_ext]['EIS']
                        dpg.add_line_series(data[data_category]['f'], data[data_category]['Re'], parent=y_axis_Re, label=f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}")

                        dpg.add_line_series(data[data_category]['f'], -data[data_category]['Im'], parent=y_axis_Im, label=f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}")

                        dpg.add_line_series(data[data_category]['Re'], -data[data_category]['Im'], parent=y_axis_Nyquist, label=f"{data_category[0].upper() + data_category[1:]}-{file_name_no_ext}")

                    dpg.add_plot_legend(parent=f"tab_drt_{data_category}_data_plot_all_Re")
                    dpg.add_plot_legend(parent=f"tab_drt_{data_category}_data_plot_all_Im")
                    dpg.add_plot_legend(parent=f"tab_drt_{data_category}_data_plot_all_ReIm")
            else:
                pass

    if config.display_file != [] and config.display_file is not None:
        print(f"---- DRT data single plots updated successfully.")
    else:
        print("---- Continue. The specified file does not exist, maybe check 'drt_plots.py' file.")