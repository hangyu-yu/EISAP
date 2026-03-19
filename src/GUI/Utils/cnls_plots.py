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
    if not dpg.does_item_exist("tab_bar_cnls_plot_single"):
        print("---- Skipped: tab_bar_cnls_plot_single not found.")
        return

    data = config.store[file_key]['CNLS']

    # Plot the DRT to identify the peaks
    try:
        if dpg.does_item_exist("tab_cnls_drt_plot_single"):
            dpg.delete_item("tab_cnls_drt_plot_single", children_only=True)
        else:
            with dpg.tab(label="DRT", tag="tab_cnls_drt_plot_single", parent="tab_bar_cnls_plot_single"):
                pass

        with dpg.plot(tag="plot_cnls_drt_single", width=-1, height=-1, no_menus=False, crosshairs=True, parent="tab_cnls_drt_plot_single"):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
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
            frequency_DRT_show = EIS_tmp['tknv_'+data_type_DRT]['ReIm']['f'] if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*EIS_tmp['tknv_'+data_type_DRT]['ReIm']['f'])
            DRT_DRT_show = EIS_tmp['tknv_'+data_type_DRT]['ReIm']['g']
            dpg.add_line_series(frequency_DRT_show, DRT_DRT_show, parent=y_axis)
            y_max_value = np.max(np.max(EIS_tmp.tknv_truncated['ReIm']['g']))
            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
            dpg.add_plot_legend()

        # Plot the residual
        if dpg.does_item_exist("tab_cnls_residual_plot_single"):
            dpg.delete_item("tab_cnls_residual_plot_single", children_only=True)
        else:
            with dpg.tab(label="Residual", tag="tab_cnls_residual_plot_single", parent="tab_bar_cnls_plot_single"):
                pass

        with dpg.group(parent="tab_cnls_residual_plot_single"):
            with dpg.plot(tag="plot_cnls_residual_single", width=-1, height=int(0.4*viewport_height), no_menus=False):
                dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]")
                if data.ResidualsReal is not None and data.ResidualsImag is not None:
                    dpg.add_scatter_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), 100 * data.ResidualsReal / np.abs(data.Ztot), parent=y_axis, label="Re")
                    dpg.add_scatter_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), 100 * data.ResidualsImag / np.abs(data.Ztot), parent=y_axis, label="Im")
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
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [ohm·cm2]")
                        if data.f is not None:
                            dpg.add_scatter_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), np.abs(data.Zmes), parent=y_axis, label="Measure")
                            dpg.add_line_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), np.abs(data.Ztot), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
                    with dpg.plot(tag="plot_phase_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Phase [deg]")
                        if data.f is not None:
                            dpg.add_scatter_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), -np.angle(data.Zmes, deg=True), parent=y_axis, label="Measure")
                            dpg.add_line_series(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), -np.angle(data.Ztot, deg=True), parent=y_axis, label="Fit")
                            dpg.add_plot_legend()
        
        if dpg.does_item_exist("tab_cnls_fit_plot_single"):
            dpg.delete_item("tab_cnls_fit_plot_single", children_only=True)
        else:
            with dpg.tab(label="Fit", tag="tab_cnls_fit_plot_single", parent="tab_bar_cnls_plot_single"):
                pass

        with dpg.table(
            tag=f"table_cnls_plot_fit",
            parent="tab_cnls_fit_plot_single",
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
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [ohm·cm2]")
                        dpg.add_scatter_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.Zmes.real, dtype=np.float32), parent=y_axis, label="Measure")
                        dpg.add_line_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.Ztot.real, dtype=np.float32), parent=y_axis, label="Fit")
                        dpg.add_plot_legend()
                    with dpg.plot(tag="plot_Im_single", width=-1, height=int(0.4*viewport_height), no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                        dpg.add_scatter_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                        dpg.add_line_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), -np.asarray(data.Ztot.imag, dtype=np.float32), parent=y_axis, label="Fit")
                        dpg.add_plot_legend()
                with dpg.table_row():
                    with dpg.plot(tag="plot_ReIm_single", width=-1, height=-1, no_menus=False, equal_aspects = True):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                        dpg.add_scatter_series(np.asarray(data.Zmes.real, dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                        dpg.add_line_series(np.asarray(data.Ztot.real, dtype=np.float32), -np.asarray(data.Ztot.imag, dtype=np.float32), parent=y_axis, label="Fit")
                        dpg.add_plot_legend()
                    with dpg.plot(tag="plot_DRT_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                        dpg.add_scatter_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.DRTmes, dtype=np.float32), parent=y_axis, label="Measure")
                        dpg.add_line_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.DRT['ReIm']['g'], dtype=np.float32), parent=y_axis, label="Fit")
                        y_max_value = np.max([np.max(np.asarray(data.DRT['ReIm']['g'], dtype=np.float32)), np.max(np.asarray(data.DRTmes, dtype=np.float32))])
                        dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                        dpg.add_plot_legend()

        # Element breakdown
        if dpg.does_item_exist("tab_cnls_element_plot_single"):
            dpg.delete_item("tab_cnls_element_plot_single", children_only=True)
        else:
            with dpg.tab(label="Elements", tag="tab_cnls_element_plot_single", parent="tab_bar_cnls_plot_single"):
                pass

        with dpg.group(parent="tab_cnls_element_plot_single"):
            with dpg.plot(tag="plot_elements_nyquist_single", width=-1, height=int(viewport_height*0.4), no_menus=False, equal_aspects = True):
                dpg.add_plot_axis(dpg.mvXAxis, label="Z' [ohm·cm2]", log_scale=False)
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                if data.Zmes is not None and data.w is not None:
                    dpg.add_scatter_series(np.asarray(data.Zmes.real, dtype=np.float32), -np.asarray(data.Zmes.imag, dtype=np.float32), parent=y_axis, label="Measure")
                    _, Z = data.EvaluateCircuit()
                    element_type_map = {elem['name']: elem['type'] for elem in data.Elements}
                    for idx, element in enumerate(Z.columns):
                        cumulative_real = sum(np.real(Z[element].iloc[-1]) for element in Z.columns[:idx])
                        if element_type_map.get(element) == 'Inductor':
                            cumulative_real = sum(
                                np.real(Z[col][0]) for col in Z.columns
                                if element_type_map.get(col) in ['Resistor', 'Gerisher', 'fFLW', 'FLW']
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
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [ohm·cm2]")
                        if data.f is not None and data.Zmes is not None and data.w is not None:
                            dpg.add_scatter_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), -np.asarray(np.imag(data.Zmes), dtype=np.float32), parent=y_axis, label="Measure")
                            for element in Z.columns:
                                dpg.add_line_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), -np.asarray(np.imag(Z[element]), dtype=np.float32), parent=y_axis, label=f"{element}")
                            dpg.add_plot_legend()

                    with dpg.plot(tag="plot_cnls_elements_DRT_single", width=-1, height=-1, no_menus=False):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]" if not dpg.get_value("check_box_cnls_tau") else "tau [s]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                        if data.f is not None and data.Zmes is not None and data.w is not None:
                            dpg.add_scatter_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.DRTmes, dtype=np.float32), parent=y_axis, label="Measure")
                            y_max_value = np.max(np.asarray(data.DRTmes, dtype=np.float32))
                            for element in data.ElementDRTs:
                                if element == 'mes':
                                    continue
                                if (element.startswith('L') and 'Randle' not in element) or (element.startswith('R') and not any(excluded in element for excluded in ['RQ', 'RC', 'Randle'])):
                                    continue
                                dpg.add_line_series(np.asarray(data.f if not dpg.get_value("check_box_cnls_tau") else 1/(2*np.pi*data.f), dtype=np.float32), np.asarray(data.ElementDRTs[element]['ReIm']['g'], dtype=np.float32), parent=y_axis, label=f"{element}")
                                y_max_value = np.max([y_max_value, np.max(np.asarray(data.ElementDRTs[element]['ReIm']['g'], dtype=np.float32))]) 
                            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            dpg.add_plot_legend()

        print("---- CNLS single plots updated successfully.")
    except:
        print("[Warning] CNLS data not updated for the selected file, which could be due to the unconsistent elements used in different files, or check cnls_plots.py_update_single_plots function.")

def update_all_plots(config):
    """Update all CNLS plots."""
    print("-- CNLS data all plots updating...")
    try:
        CNLS_tmp = config.store[os.path.splitext(config.display_file)[0]]['CNLS']
        if CNLS_tmp.Elements is None:
            print("---- CNLS all plots skipped: no elements found.")
            return

        name_list = [element['name'] for element in CNLS_tmp.Elements]
        valid_element_tabs = set()

        if config.fix_all_plots_CNLS:
            source_files = [os.path.basename(file_name) for file_name in config.file_list]
        else:
            source_files = list(config.selected_files)

        for idx, param_name in enumerate(name_list):
            element_tab = f"tab_cnls_all_{param_name}"
            valid_element_tabs.add(element_tab)

            if not dpg.does_item_exist(element_tab):
                with dpg.tab(label=param_name, tag=element_tab, parent="tab_bar_cnls_plot_all"):
                    pass

            param_tab_bar = f"tab_bar_cnls_all_{param_name}"
            if not dpg.does_item_exist(param_tab_bar):
                with dpg.tab_bar(tag=param_tab_bar, parent=element_tab):
                    pass

            start_idx = CNLS_tmp.ElementsStartIndex[idx]
            end_idx = CNLS_tmp.ElementsEndIndex[idx]
            valid_param_tabs = set()

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

                param_tab = f"tab_cnls_all_{param}"
                valid_param_tabs.add(param_tab)
                if not dpg.does_item_exist(param_tab):
                    with dpg.tab(label=param, tag=param_tab, parent=param_tab_bar):
                        pass

                dpg.delete_item(param_tab, children_only=True)
                with dpg.group(parent=param_tab):
                    with dpg.plot(tag=f"plot_cnls_all_{param}", width=-1, height=-1, no_menus=False):
                        x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Measurements", log_scale=False)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)

                        for file_name in source_files:
                            file_key = os.path.splitext(file_name)[0]
                            file_name_list.append(gui_utils.small_functions.string_abbreviation(file_key, 3, 5))
                            if file_key not in config.store:
                                print(f"[Warning] File {file_key} not found in config store. Skipping...")
                                continue
                            cnls_file = config.store[file_key]['CNLS']
                            value = cnls_file.ElementsParamValues[para_idx]
                            data_list.append(value)
                            y_min_value = np.min([y_min_value, value])
                            y_max_value = np.max([y_max_value, value])

                        x_data = list(range(1, len(file_name_list) + 1))
                        label_pairs = tuple(zip(file_name_list, x_data))
                        dpg.add_line_series(x_data, data_list, parent=y_axis)
                        dpg.add_scatter_series(x_data, data_list, parent=y_axis)
                        dpg.set_axis_limits(y_axis, y_min_value * 0.5, y_max_value * 1.1)
                        dpg.set_axis_limits(x_axis, 0, len(file_name_list) + 1)
                        dpg.set_axis_ticks(x_axis, label_pairs)

            # Remove stale parameter tabs if definitions changed.
            tab_children = dpg.get_item_children(param_tab_bar)
            for child in tab_children[1]:
                if isinstance(child, str) and child.startswith("tab_cnls_all_") and child not in valid_param_tabs:
                    dpg.delete_item(child)

        # Remove tabs that are no longer needed.
        if dpg.does_item_exist("tab_bar_cnls_plot_all"):
            children = dpg.get_item_children("tab_bar_cnls_plot_all")
            for child in children[1]:
                if isinstance(child, str) and child.startswith("tab_cnls_all_") and child not in valid_element_tabs:
                    dpg.delete_item(child)

        print("---- CNLS all plots updated successfully.")
    except:
        print("[Warning] CNLS data not updated for all the files, which could be due to the unconsistent elements used in different files, or check cnls_plots.py_update_all_plots function.")
