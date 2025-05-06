import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def update_single_plots(config):
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    """Update single-file DRT plots."""
    print("-- Updating DRT single plots...")
    try:
        if config.display_file is None or os.path.splitext(config.display_file)[0] not in config.store or config.store[os.path.splitext(config.display_file)[0]]['EIS'].tknv_truncated is None:
            print("---- Skipped: No valid file selected.")
            return
    except:
        print("---- Skipped: No valid file selected.")
        return

    file_key = os.path.splitext(config.display_file)[0]
    data = config.store[file_key]['CNLS']

    # Plot the residual
    dpg.delete_item("tab_cnls_residual_plot_single")
    with dpg.tab(label="Residual", tag="tab_cnls_residual_plot_single", parent="tab_bar_cnls_plot_single"):
        with dpg.plot(tag="plot_cnls_residual_single", width=-1, height=-1, no_menus=True):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]")
            dpg.add_scatter_series(data.f, 100 * data.ResidualsReal / np.abs(data.Ztot), parent=y_axis, label="Re")
            dpg.add_scatter_series(data.f, 100 * data.ResidualsImag / np.abs(data.Ztot), parent=y_axis, label="Im")
            dpg.add_plot_legend()
            
    with dpg.tab(label="Fit", tag="tab_cnls_fit_plot_single", parent="tab_bar_cnls_plot_single"):
        with dpg.table(
            parent=f"tab_cnls_fit_plot_single",
            tag=f"table_cnls_fit_plot_single",
            header_row=False,
            borders_innerV=False,  # Show vertical column lines
            borders_outerV=False,
            borders_outerH=False,
            row_background=False,  # Enable alternating row colors
            reorderable=False,     # Allow column reordering via drag-and-drop
            scrollX=True,         # Enable horizontal scrolling
            scrollY=True,         # Enable vertical scrolling
            policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
        ):
            dpg.add_table_column(label="ID", width_stretch=True)
            dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
            with dpg.table_row():
                with dpg.plot(tag="plot_module_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [ohm·cm2]")
                    dpg.add_scatter_series(data.f, np.abs(data.Zmes), parent=y_axis, label="Measure")
                    dpg.add_line_series(data.f, np.abs(data.Ztot), parent=y_axis, label="Fit")
                    dpg.add_plot_legend()
                with dpg.plot(tag="plot_phase_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [ohm·cm2]")
                    dpg.add_scatter_series(data.f, -np.angle(data.Zmes, deg=True), parent=y_axis, label="Measure")
                    dpg.add_line_series(data.f, -np.angle(data.Ztot, deg=True), parent=y_axis, label="Fit")
                    dpg.add_plot_legend()
            with dpg.table_row():
                with dpg.plot(tag="plot_Re_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [ohm·cm2]")
                    dpg.add_scatter_series(data.f, data.Zmes.real, parent=y_axis, label="Measure")
                    dpg.add_line_series(data.f, data.Ztot.real, parent=y_axis, label="Fit")
            
                with dpg.plot(tag="plot_Im_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                    dpg.add_scatter_series(data.f, -data.Zmes.imag, parent=y_axis, label="Measure")
                    dpg.add_line_series(data.f, -data.Ztot.imag, parent=y_axis, label="Fit")
            with dpg.table_row():
                with dpg.plot(tag="plot_ReIm_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                    dpg.add_scatter_series(data.Zmes.real, -data.Zmes.imag, parent=y_axis, label="Measure")
                    dpg.add_line_series(data.Ztot.real, -data.Ztot.imag, parent=y_axis, label="Fit")
                with dpg.plot(tag="plot_DRT_single", width=-1, height=int(0.33*viewport_height), no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                    dpg.add_scatter_series(data.f, data.DRTmes, parent=y_axis, label="Measure")
                    dpg.add_line_series(data.f, data.DRT['ReIm']['g'], parent=y_axis, label="Fit")
                    y_max_value = np.nax[np.max(data.DRT['ReIm']['g']), np.max(data.DRTmes)]
                    dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)

    # Element breakdown
    with dpg.tab(label="Elements", tag="tab_cnls_element_plot_single", parent="tab_bar_cnls_plot_single"):
        with dpg.plot(tag="plot_elements_nyquist_single", width=-1, height=viewport_height*0.5, no_menus=True):
            dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
            dpg.add_scatter_series(data.Zmes.real, -data.Zmes.imag, parent=y_axis, label="Measure")
            _, Z = data.EvaluateCircuit()
            for element in Z.columns:
                dpg.add_line_series(Z[element].real, Z[element].imag, parent=y_axis, label=f"{element}")
        
        with dpg.table(
            parent=f"tab_cnls_element_plot_single",
            tag=f"table_cnls_elements_Im_DRT_single",
            header_row=False,
            borders_innerV=False,  # Show vertical column lines
            borders_outerV=False,
            borders_outerH=False,
            row_background=False,  # Enable alternating row colors
            reorderable=False,     # Allow column reordering via drag-and-drop
            scrollX=True,         # Enable horizontal scrolling
            scrollY=True,         # Enable vertical scrolling
            policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
        ):
            dpg.add_table_column(width_stretch=True)
            dpg.add_table_column(width_stretch=True)
            with dpg.table_row():
                with dpg.plot(tag="plot_elements_Im_single", width=-1, height=-1, no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                    dpg.add_scatter_series(data.f, -data.Zmes.imag, parent=y_axis, label="Measure")
                    for element in Z.columns:
                        dpg.add_line_series(data.f, -Z[element].imag, parent=y_axis, label=f"{element}")

                with dpg.plot(tag="plot_elements_DRT_single", width=-1, height=-1, no_menus=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                    y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                    dpg.add_scatter_series(data.f, data.DRTmes, parent=y_axis, label="Measure")
                    for element in data.ElementDRTs:
                        if 'L' in element or ('R' in element and not any(excluded in element for excluded in ['RQ', 'RC', 'Randle'])):
                            continue
                        dpg.add_line_series(data.f, data.ElementDRTs[element]['ReIm']['g'], parent=y_axis, label=f"{element}")


    print("---- CNLS single plots updated successfully.")

def update_all_plots(config):
    # """Update multi-file DRT comparison plots (gamma distribution only)."""
    # print("-- Updating DRT gamma distribution plots...")
    
    # if not config.selected_files:
    #     print("---- Skipped: No files selected.")
    #     return

    # # Define data types and categories
    # data_types = ["truncated", "smooth", "LCcorrect", "extrapolation"]
    # data_categories = ["ReIm", "Re", "Im"]

    # for data_type in data_types:
    #     # Delete old tabs and create new tabs
    #     dpg.delete_item(f"tab_drt_{data_type}_plot_all")
    #     with dpg.tab(label=data_type.capitalize(), tag=f"tab_drt_{data_type}_plot_all", parent="tab_bar_drt_plot_all"):
            
    #         # Create category tabs under data_type
    #         dpg.delete_item(f"tab_bar_{data_type}_categories_all")
    #         with dpg.tab_bar(tag=f"tab_bar_{data_type}_categories_all", parent=f"tab_drt_{data_type}_plot_all"):
                
    #             for category in data_categories:
    #                 # Delete old category tabs and create new tabs
    #                 dpg.delete_item(f"tab_drt_{data_type}_{category}_all")
    #                 with dpg.tab(label=category, tag=f"tab_drt_{data_type}_{category}_all"):
                        
    #                     # Create gamma distribution plot
    #                     with dpg.plot(
    #                         tag=f"plot_gamma_{data_type}_{category}_all",
    #                         width=-1,
    #                         height=-1,  # Adaptive height
    #                         no_menus=True
    #                     ):
    #                         # X-axis (log scale)
    #                         dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            
    #                         # Y-axis
    #                         y_axis = dpg.add_plot_axis(
    #                             dpg.mvYAxis, 
    #                             label="gamma [ohm·s·cm2]",
    #                             tag=f"y_axis_{data_type}_{category}_all"
    #                         )
                            
    #                         # Iterate through all files and add data
    #                         y_max_value = 0
    #                         for file_name in config.selected_files:
    #                             file_key = os.path.splitext(file_name)[0]
    #                             if file_key in config.store and 'EIS' in config.store[file_key]:
    #                                 data = config.store[file_key]['EIS']
    #                                 if data[f"tknv_{data_type}"] is not None:
    #                                     _add_series_to_plot(
    #                                         {
    #                                             'f': data[f"tknv_{data_type}"][category]['f'],
    #                                             'y': data[f"tknv_{data_type}"][category]['g']
    #                                         },
    #                                         y_axis,
    #                                         label=gui_utils.small_functions.string_abbreviation(file_key, 12, 12),
    #                                         is_line=True
    #                                     )
    #                                     if np.max(data[f"tknv_{data_type}"][category]['g']) > y_max_value:
    #                                         y_max_value = np.max(data[f"tknv_{data_type}"][category]['g'])

    #                         dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            
    #                         # Add legend
    #                         dpg.add_plot_legend(
    #                             parent=f"plot_gamma_{data_type}_{category}_all",
    #                             location=dpg.mvPlot_Location_NorthEast  # Legend position at top-right
    #                         )

    print("---- DRT gamma distribution plots updated successfully.")
