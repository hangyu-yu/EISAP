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
    if config.store[file_key]['CNLS'].DRTmes is not None:
        config.store[file_key]['CNLS'].DRTmes = config.store[file_key]['EIS']['tknv_' + config.store[file_key]['CNLS'].data_type.replace('_KK', '').replace('_DRT', '')]['ReIm']['g']
        config.store[file_key]['CNLS'].f = config.store[file_key]['EIS']['tknv_' + config.store[file_key]['CNLS'].data_type.replace('_KK', '').replace('_DRT', '')]['ReIm']['f']
        if config.store[file_key]['CNLS'].data_type == 'smooth_KK':
            config.store[file_key]['CNLS'].Zmes = config.store[file_key]['EIS']['smooth']['Z']
        elif config.store[file_key]['CNLS'].data_type == 'smooth_DRT':
            config.store[file_key]['CNLS'].DRTmes = config.store[file_key]['EIS']['tknv_truncated']['ReIm']['g']
            config.store[file_key]['CNLS'].f = config.store[file_key]['EIS']['tknv_truncated']['ReIm']['f']
            config.store[file_key]['CNLS'].Zmes = config.store[file_key]['EIS']['tknv_truncated']['ReIm']['Re']+1j*config.store[file_key]['EIS']['tknv_truncated']['ReIm']['Im']
        else:
            config.store[file_key]['CNLS'].Zmes = config.store[file_key]['EIS'][config.store[file_key]['CNLS'].data_type]['Z']
    if config.store[file_key]['CNLS'].f is not None:
        config.store[file_key]['CNLS'].w = config.store[file_key]['CNLS'].f * 2 * np.pi
    data = config.store[file_key]['CNLS']

    # Plot the DRT to identify the peaks
    try:
        dpg.delete_item("tab_cnls_drt_plot_single")
        with dpg.tab(label="DRT", tag="tab_cnls_drt_plot_single", parent="tab_bar_cnls_plot_single"):
            with dpg.plot(tag="plot_cnls_drt_single", width=-1, height=-1, no_menus=False, crosshairs=True):
                dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                file_name_no_ext = os.path.splitext(config.display_file)[0]
                data_type_DRT = dpg.get_value('combo_cnls_data_type')
                EIS_tmp = config.store[file_key]['EIS']
                if data_type_DRT == 'smooth_KK':
                    data_type_DRT = 'smooth'
                elif data_type_DRT == 'LCcorrected':
                    data_type_DRT = 'LCcorrect'
                elif data_type_DRT == 'smooth_DRT':
                    data_type_DRT = 'truncated'
                frequency_DRT_show = EIS_tmp['tknv_'+data_type_DRT]['ReIm']['f']
                DRT_DRT_show = EIS_tmp['tknv_'+data_type_DRT]['ReIm']['g']
                dpg.add_line_series(frequency_DRT_show, DRT_DRT_show, parent=y_axis)
                y_max_value = np.max(np.max(EIS_tmp.tknv_truncated['ReIm']['g']))
                dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                dpg.add_plot_legend()

        # Plot the residual
        dpg.delete_item("tab_cnls_residual_plot_single")
        with dpg.tab(label="Residual", tag="tab_cnls_residual_plot_single", parent="tab_bar_cnls_plot_single"):
            with dpg.plot(tag="plot_cnls_residual_single", width=-1, height=int(0.4*viewport_height), no_menus=False):
                dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]")
                if data.ResidualsReal is not None and data.ResidualsImag is not None:
                    dpg.add_scatter_series(data.f, 100 * data.ResidualsReal / np.abs(data.Ztot), parent=y_axis, label="Re")
                    dpg.add_scatter_series(data.f, 100 * data.ResidualsImag / np.abs(data.Ztot), parent=y_axis, label="Im")
                    dpg.add_plot_legend()
            with dpg.table(
                tag=f"table_cnls_plot_residuals",
                reorderable=False, # Allow column reordering via drag-and-drop
                header_row=False,  # Hide the header row
                scrollX=True,      # Enable horizontal scrolling
                scrollY=True,      # Enable vertical scrolling
                policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
            ):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_stretch=True)
                with dpg.table_row():
                    with dpg.plot(tag="plot_module_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [ohm·cm2]")
                        if data.f is not None:
                            dpg.add_scatter_series(data.f, np.abs(data.Zmes), parent=y_axis, label="Measure")
                            dpg.add_line_series(data.f, np.abs(data.Ztot), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
                    with dpg.plot(tag="plot_phase_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Phase [deg]")
                        if data.f is not None:
                            dpg.add_scatter_series(data.f, -np.angle(data.Zmes, deg=True), parent=y_axis, label="Measure")
                            dpg.add_line_series(data.f, -np.angle(data.Ztot, deg=True), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
        
        dpg.delete_item("tab_cnls_fit_plot_single")
        with dpg.tab(label="Fit", tag="tab_cnls_fit_plot_single", parent="tab_bar_cnls_plot_single"):
            with dpg.table(
                tag=f"table_cnls_plot_fit",
                reorderable=False, # Allow column reordering via drag-and-drop
                header_row=False,  # Hide the header row
                scrollX=True,      # Enable horizontal scrolling
                scrollY=True,      # Enable vertical scrolling
                policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
            ):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_stretch=True)
                if data.f is not None:
                    with dpg.table_row():
                        with dpg.plot(tag="plot_Re_single", width=-1, height=int(0.4*viewport_height), no_menus=False):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [ohm·cm2]")
                            dpg.add_scatter_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.Zmes.real, dtype=np.float32), parent=y_axis, label="Measure")
                            dpg.add_line_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.Ztot.real, dtype=np.float32), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
                        with dpg.plot(tag="plot_Im_single", width=-1, height=int(0.4*viewport_height), no_menus=False):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                            dpg.add_scatter_series(np.asarray(data.f, dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                            dpg.add_line_series(np.asarray(data.f, dtype=np.float32), -np.asarray(data.Ztot.imag, dtype=np.float32), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
                    with dpg.table_row():
                        with dpg.plot(tag="plot_ReIm_single", width=-1, height=-1, no_menus=False, equal_aspects = True):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                            dpg.add_scatter_series(np.asarray(data.Zmes.real, dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                            dpg.add_line_series(np.asarray(data.Ztot.real, dtype=np.float32), -np.asarray(data.Ztot.imag, dtype=np.float32), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
                        with dpg.plot(tag="plot_DRT_single", width=-1, height=-1, no_menus=False):
                            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                            dpg.add_scatter_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.DRTmes, dtype=np.float32), parent=y_axis, label="Measure")
                            dpg.add_line_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.DRT['ReIm']['g'], dtype=np.float32), parent=y_axis, label="Fit")
                            y_max_value = np.max([np.max(np.asarray(data.DRT['ReIm']['g'], dtype=np.float32)), np.max(np.asarray(data.DRTmes, dtype=np.float32))])
                            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            dpg.add_plot_legend()

    # Element breakdown
        dpg.delete_item("tab_cnls_element_plot_single")
        with dpg.tab(label="Elements", tag="tab_cnls_element_plot_single", parent="tab_bar_cnls_plot_single"):
            with dpg.plot(tag="plot_elements_nyquist_single", width=-1, height=int(viewport_height*0.4), no_menus=False, equal_aspects = True):
                dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                if data.Zmes is not None and data.w is not None:
                    dpg.add_scatter_series(np.asarray(data.Zmes.real, dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                    _, Z = data.EvaluateCircuit()
                    for idx, element in enumerate(Z.columns):
                        cumulative_real = sum(np.real(Z[element].iloc[-1]) for element in Z.columns[:idx])
                        if 'L' in element:
                            cumulative_real = sum(
                                np.real(Z[col][0]) for col in Z.columns
                                if 'R' in col and not any(excluded in col for excluded in ['RQ', 'RC', 'Randle'])
                            )
                        dpg.add_line_series(np.asarray(np.real(Z[element])+cumulative_real, dtype=np.float32), -np.asarray(np.imag(Z[element]), dtype=np.float32), parent=y_axis, label=f"{element}")
                    dpg.add_plot_legend()

            with dpg.table(
                tag=f"table_cnls_plot_elements",
                reorderable=False, # Allow column reordering via drag-and-drop
                header_row=False,  # Hide the header row
                scrollX=True,      # Enable horizontal scrolling
                scrollY=True,      # Enable vertical scrolling
                policy=dpg.mvTable_SizingFixedFit,  # Automatically adjust column width
            ):
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_stretch=True)
                with dpg.table_row():
                    with dpg.plot(tag="plot_cnls_elements_Im_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                        if data.f is not None and data.Zmes is not None and data.w is not None:
                            dpg.add_scatter_series(np.asarray(data.f, dtype=np.float32), -np.asarray(np.imag(data.Zmes), dtype=np.float32), parent=y_axis, label="Measure")
                            for element in Z.columns:
                                dpg.add_line_series(np.asarray(data.f, dtype=np.float32), -np.asarray(np.imag(Z[element]), dtype=np.float32), parent=y_axis, label=f"{element}")
                            dpg.add_plot_legend()

                    with dpg.plot(tag="plot_cnls_elements_DRT_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                        if data.f is not None and data.Zmes is not None and data.w is not None:
                            dpg.add_scatter_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.DRTmes, dtype=np.float32), parent=y_axis, label="Measure")
                            y_max_value = np.max(np.asarray(data.DRTmes, dtype=np.float32))
                            for element in data.ElementDRTs:
                                if 'L' in element or ('R' in element and not any(excluded in element for excluded in ['RQ', 'RC', 'Randle'])):
                                    continue
                                dpg.add_line_series(np.asarray(data.f, dtype=np.float32), np.asarray(data.ElementDRTs[element]['ReIm']['g'], dtype=np.float32), parent=y_axis, label=f"{element}")
                                y_max_value = np.max([y_max_value, np.max(np.asarray(data.ElementDRTs[element]['ReIm']['g'], dtype=np.float32))]) 
                            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            dpg.add_plot_legend()

        print("---- CNLS single plots updated successfully.")
    except:
        print("[Warning] CNLS data not updated for the selected file, which could be due to the unconsistent elements used in different files, or check cnls_plots.py_update_single_plots function.")

def update_all_plots(config):
    """Update all CNLS plots."""
    if config.fix_all_plots_CNLS:
        print("-- CNLS data all plots updating...")
        try:
            CNLS_tmp = config.store[os.path.splitext(config.display_file)[0]]['CNLS']
            if CNLS_tmp.Elements is not None:
                name_list = [element['name'] for element in CNLS_tmp.Elements]
                children = dpg.get_item_children("tab_bar_cnls_plot_all")
                for child in children[1]:
                    dpg.delete_item(child)
                for idx, param_name in enumerate(name_list):
                    with dpg.tab(label=param_name, tag=f"tab_cnls_all_{param_name}", parent="tab_bar_cnls_plot_all"):
                        with dpg.tab_bar(tag=f"tab_bar_cnls_all_{param_name}", parent = f"tab_cnls_all_{param_name}"):
                            start_idx = CNLS_tmp.ElementsStartIndex[idx]
                            end_idx = CNLS_tmp.ElementsEndIndex[idx]
                            for para_idx in range(start_idx, end_idx + 1):
                                file_name_list = []
                                data_list = []
                                y_min_value = 0.00
                                y_max_value = 0.00
                                param = CNLS_tmp.ElementsParamNames[para_idx]
                                if 'tau' in param.split('_')[1]:
                                    y_label = "tau [s]"
                                elif 'R' in param.split('_')[1]:
                                    y_label = "Resistance [ohm·cm2]"
                                elif 'alpha' in param.split('_')[1]:
                                    y_label = "Dispersion factor"
                                elif 'L' in param.split('_')[1]:
                                    y_label = "Inductance [H·cm2]"
                                else:
                                    y_label = "Unit"
                                with dpg.tab(label=param, tag=f"tab_cnls_all_{param}", parent=f"tab_bar_cnls_all_{param_name}"):
                                    with dpg.plot(tag=f"plot_cnls_all_{param}", width=-1, height=-1, no_menus=False):
                                        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Measurements", log_scale=False)
                                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)
                                        for file_name in config.file_list:
                                            file_name = os.path.basename(file_name)
                                            file_name_list.append(gui_utils.small_functions.string_abbreviation(os.path.splitext(file_name)[0], 3, 5))
                                            file_key = os.path.splitext(file_name)[0]
                                            if file_key not in config.store:
                                                print(f"[Warning] File {file_key} not found in config store. Skipping...")
                                                continue
                                            CNLS_tmp = config.store[file_key]['CNLS']
                                            data_list.append(CNLS_tmp.ElementsParamValues[para_idx])
                                            y_min_value = np.min([y_min_value, CNLS_tmp.ElementsParamValues[para_idx]])
                                            y_max_value = np.max([y_max_value, CNLS_tmp.ElementsParamValues[para_idx]])
                                        x_data = list(range(1, len(file_name_list) + 1))
                                        label_pairs = tuple(zip(file_name_list, x_data))
                                        dpg.add_line_series(x_data, data_list, parent=y_axis)
                                        dpg.add_scatter_series(x_data, data_list, parent=y_axis)
                                        dpg.set_axis_limits(y_axis, y_min_value*0.5, y_max_value * 1.1)
                                        dpg.set_axis_limits(x_axis, 0, len(file_name_list) + 1)
                                        dpg.set_axis_ticks(x_axis, label_pairs)

            print("---- DRT gamma distribution plots updated successfully.")
        except:
            print("[Warning] CNLS data not updated for all the files, which could be due to the unconsistent elements used in different files, or check cnls_plots.py_update_all_plots function.")
    else:
        print("-- CNLS data all plots updating...")
        try:
            CNLS_tmp = config.store[os.path.splitext(config.display_file)[0]]['CNLS']
            if CNLS_tmp.Elements is not None:
                name_list = [element['name'] for element in CNLS_tmp.Elements]
                children = dpg.get_item_children("tab_bar_cnls_plot_all")
                for child in children[1]:
                    dpg.delete_item(child)
                for idx, param_name in enumerate(name_list):
                    with dpg.tab(label=param_name, tag=f"tab_cnls_all_{param_name}", parent="tab_bar_cnls_plot_all"):
                        with dpg.tab_bar(tag=f"tab_bar_cnls_all_{param_name}", parent = f"tab_cnls_all_{param_name}"):
                            start_idx = CNLS_tmp.ElementsStartIndex[idx]
                            end_idx = CNLS_tmp.ElementsEndIndex[idx]
                            for para_idx in range(start_idx, end_idx + 1):
                                file_name_list = []
                                data_list = []
                                y_min_value = 0.00
                                y_max_value = 0.00
                                param = CNLS_tmp.ElementsParamNames[para_idx]
                                if 'tau' in param.split('_')[1]:
                                    y_label = "tau [s]"
                                elif 'R' in param.split('_')[1]:
                                    y_label = "Resistance [ohm·cm2]"
                                elif 'alpha' in param.split('_')[1]:
                                    y_label = "Dispersion factor"
                                elif 'L' in param.split('_')[1]:
                                    y_label = "Inductance [H·cm2]"
                                else:
                                    y_label = "Unit"
                                with dpg.tab(label=param, tag=f"tab_cnls_all_{param}", parent=f"tab_bar_cnls_all_{param_name}"):
                                    with dpg.plot(tag=f"plot_cnls_all_{param}", width=-1, height=-1, no_menus=False):
                                        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Measurements", log_scale=False)
                                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)
                                        for file_name in config.selected_files:
                                            file_name_list.append(gui_utils.small_functions.string_abbreviation(os.path.splitext(file_name)[0], 3, 5))
                                            file_key = os.path.splitext(file_name)[0]
                                            CNLS_tmp = config.store[file_key]['CNLS']
                                            data_list.append(CNLS_tmp.ElementsParamValues[para_idx])
                                            y_min_value = np.min([y_min_value, CNLS_tmp.ElementsParamValues[para_idx]])
                                            y_max_value = np.max([y_max_value, CNLS_tmp.ElementsParamValues[para_idx]])
                                        x_data = list(range(1, len(file_name_list) + 1))
                                        label_pairs = tuple(zip(file_name_list, x_data))
                                        dpg.add_line_series(x_data, data_list, parent=y_axis)
                                        dpg.add_scatter_series(x_data, data_list, parent=y_axis)
                                        dpg.set_axis_limits(y_axis, y_min_value*0.5, y_max_value * 1.1)
                                        dpg.set_axis_limits(x_axis, 0, len(file_name_list) + 1)
                                        dpg.set_axis_ticks(x_axis, label_pairs)

            print("---- DRT gamma distribution plots updated successfully.")
        except:
            print("[Warning] CNLS data not updated for all the files, which could be due to the unconsistent elements used in different files, or check cnls_plots.py_update_all_plots function.")
