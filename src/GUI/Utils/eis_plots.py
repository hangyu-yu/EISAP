import os
import numpy as np
import dearpygui.dearpygui as dpg

def update_single_plot(config):
    """
    Update the table with the latest data from EIS and CNLS.

    Parameters:
    - config: Configuration object containing settings and paths.
    - EIS: EIS object containing the latest data.
    - CNLS: CNLS object containing the latest data.
    - data_type: Type of data to be displayed in the table.
    """
    for idx, data_category in enumerate(["KK_data", "raw", "truncated", "LCcorrect", "smooth",  "extrapolation"]):
        dpg.delete_item(f"tab_eis_{data_category}_plot")
        with dpg.tab(label=data_category, tag=f"tab_eis_{data_category}_plot", parent="tab_bar_eis_plot_single"):
            if config.display_file != [] and os.path.splitext(config.display_file)[0] in config.store.keys():
                print("-- Updating plot:", data_category)
                # Clear existing table rows
                dpg.delete_item(f"tab_eis_{data_category}_data_plot")
                data = config.store[os.path.splitext(config.display_file)[0]]['EIS']

                # Reconstruct the table with new data
                if data_category != "KK_data":
                    pass
                else:
                    # Plot KK results
                    with dpg.plot(
                        label="Karmar-Kronig results",
                        tag=f"tab_eis_{data_category}_data_plot_KK",
                        width = -1,
                        height=int(dpg.get_item_height(f"tab_eis_{data_category}_plot") / 2),
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
                        label="Raw impedance and phase",
                        tag=f"tab_eis_{data_category}_data_plot_Z_phase",
                        width = -1,
                        height= -1,
                        no_menus=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis1 = dpg.add_plot_axis(dpg.mvYAxis, label="Resistance [Ohm·cm2]")
                        # dpg.set_axis_limits(y_axis1, 0, 1.1 * np.max(abs(data['raw']['Z'])))
                        dpg.add_scatter_series(data['raw']['f'], abs(data['raw']['Z']), parent=y_axis1, label="Z")

                        y_axis2 = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True)
                        # dpg.set_axis_limits(y_axis2, 0, 1.1 * np.max(-np.degrees(np.angle(data['raw']['Z']))))
                        dpg.add_scatter_series(data['raw']['f'], -np.degrees(np.angle(data['raw']['Z'])), parent=y_axis2, label="Phase")
                        dpg.add_plot_legend()
            
                print(f"---- Table {data_category} updated successfully.")
            else:
                print("---- Continue. The specified file does not exist, check 'eis_table.py' file.")
                pass

def update_all_plots(config, table_theme):
    pass