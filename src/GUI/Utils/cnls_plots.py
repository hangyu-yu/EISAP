import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def _ensure_contiguous(data):
    """Ensure that NumPy arrays are C-contiguous and handle NaN values."""
    if isinstance(data, dict):
        return {k: np.ascontiguousarray(v) if isinstance(v, np.ndarray) else v for k, v in data.items()}
    return np.ascontiguousarray(data)

def _create_plot_with_axes(parent_tag, width, height, x_label, y_label, log_x=False):
    """Create a plot area with axes."""
    with dpg.plot(tag=parent_tag, width=width, height=height, no_menus=True):
        dpg.add_plot_axis(dpg.mvXAxis, label=x_label, log_scale=log_x)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)
        return y_axis

def _add_series_to_plot(plot_data, y_axis, label, is_line=True):
    """Add a line or scatter series to the plot."""
    x_data = _ensure_contiguous(plot_data['f'])
    y_data = _ensure_contiguous(plot_data['y'])
    if is_line:
        dpg.add_line_series(x_data, y_data, parent=y_axis, label=label)
    else:
        dpg.add_scatter_series(x_data, y_data, parent=y_axis, label=label)

def _update_bode_plots(data, parent_tag, data_category):
    """Update Bode plots (Re and Im)."""
    # Real part (Z')
    y_axis_re = _create_plot_with_axes(
        f"{parent_tag}_Re", -1, int(dpg.get_viewport_height() * 0.25),
        "Frequency [Hz]", "Z' [Ohm·cm2]", log_x=True
    )
    _add_series_to_plot({'f': data.truncated['f'], 'y': data.truncated['Re']}, y_axis_re, f"{data_category}_truncated", False)
    _add_series_to_plot({'f': data.smooth['f'], 'y': data.smooth['Re']}, y_axis_re, f"{data_category}_KK_smooth")
    _add_series_to_plot({'f': data.tknv_truncated[data_category]['f'], 'y': data.tknv_truncated[data_category]['Re']}, y_axis_re, f"{data_category}_DRT_smooth")
    dpg.add_plot_legend(parent=f"{parent_tag}_Re")

    # Imaginary part (-Z'')
    y_axis_im = _create_plot_with_axes(
        f"{parent_tag}_Im", -1, int(dpg.get_viewport_height() * 0.25),
        "Frequency [Hz]", "-Z'' [Ohm·cm2]", log_x=True
    )
    _add_series_to_plot({'f': data.truncated['f'], 'y': -data.truncated['Im']}, y_axis_im, f"{data_category}_truncated", False)
    _add_series_to_plot({'f': data.smooth['f'], 'y': -data.smooth['Im']}, y_axis_im, f"{data_category}_KK_smooth")
    _add_series_to_plot({'f': data.tknv_truncated[data_category]['f'], 'y': -data.tknv_truncated[data_category]['Im']}, y_axis_im, f"{data_category}_DRT_smooth")
    dpg.add_plot_legend(parent=f"{parent_tag}_Im")

def _update_nyquist_plot(data, parent_tag, data_category):
    """Update Nyquist plot."""
    y_axis = _create_plot_with_axes(
        f"{parent_tag}_ReIm", -1, -1,
        "Z' [Ohm·cm2]", "-Z'' [Ohm·cm2]"
    )
    _add_series_to_plot({'f': data.truncated['Re'], 'y': -data.truncated['Im']}, y_axis, f"{data_category}_truncated", False)
    _add_series_to_plot({'f': data.smooth['Re'], 'y': -data.smooth['Im']}, y_axis, f"{data_category}_KK_smooth")
    _add_series_to_plot({'f': data.tknv_truncated[data_category]['Re'], 'y': -data.tknv_truncated[data_category]['Im']}, y_axis, f"{data_category}_DRT_smooth")
    dpg.add_plot_legend(parent=f"{parent_tag}_ReIm")

def update_single_plots(config):
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
    data = config.store[file_key]['EIS']

    for data_type in ["truncated", "smooth", "LCcorrect", "extrapolation", "EIS_truncated"]:
        dpg.delete_item(f"tab_drt_{data_type}_plot_single")
        with dpg.tab(label=data_type.capitalize(), tag=f"tab_drt_{data_type}_plot_single", parent="tab_bar_drt_plot_single"):
            if data_type != "EIS_truncated":
                if data[f"tknv_{data_type}"]:
                    dpg.delete_item(f"tab_drt_{data_type}_data_plot_single")
                    with dpg.plot(tag=f"tab_drt_{data_type}_data_plot_single", width=-1, height=-1, no_menus=True):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")
                        y_max_value = 0
                        for category in ["ReIm", "Re", "Im"]:
                            if np.max(data[f"tknv_{data_type}"][category]['g']) > y_max_value:
                                y_max_value = np.max(data[f"tknv_{data_type}"][category]['g'])
                            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            _add_series_to_plot(
                                {'f': data[f"tknv_{data_type}"][category]['f'], 'y': data[f"tknv_{data_type}"][category]['g']},
                                y_axis, category
                            )
                        dpg.add_plot_legend()
            else:
                dpg.delete_item(f"tab_bar_drt_{data_type}_plot_single")
                with dpg.tab_bar(tag=f"tab_bar_drt_{data_type}_plot_single", parent=f"tab_drt_{data_type}_plot_single"):
                    for category in ["ReIm", "Re", "Im"]:
                        dpg.delete_item(f"tab_drt_{data_type}_{category}_plot_single")
                        with dpg.tab(label=category, tag=f"tab_drt_{data_type}_{category}_plot_single"):
                            _update_bode_plots(data, f"tab_drt_{data_type}_{category}", category)
                            _update_nyquist_plot(data, f"tab_drt_{data_type}_{category}", category)

    print("---- DRT single plots updated successfully.")

def update_all_plots(config):
    """Update multi-file DRT comparison plots (gamma distribution only)."""
    print("-- Updating DRT gamma distribution plots...")
    
    if not config.selected_files:
        print("---- Skipped: No files selected.")
        return

    # Define data types and categories
    data_types = ["truncated", "smooth", "LCcorrect", "extrapolation"]
    data_categories = ["ReIm", "Re", "Im"]

    for data_type in data_types:
        # Delete old tabs and create new tabs
        dpg.delete_item(f"tab_drt_{data_type}_plot_all")
        with dpg.tab(label=data_type.capitalize(), tag=f"tab_drt_{data_type}_plot_all", parent="tab_bar_drt_plot_all"):
            
            # Create category tabs under data_type
            dpg.delete_item(f"tab_bar_{data_type}_categories_all")
            with dpg.tab_bar(tag=f"tab_bar_{data_type}_categories_all", parent=f"tab_drt_{data_type}_plot_all"):
                
                for category in data_categories:
                    # Delete old category tabs and create new tabs
                    dpg.delete_item(f"tab_drt_{data_type}_{category}_all")
                    with dpg.tab(label=category, tag=f"tab_drt_{data_type}_{category}_all"):
                        
                        # Create gamma distribution plot
                        with dpg.plot(
                            tag=f"plot_gamma_{data_type}_{category}_all",
                            width=-1,
                            height=-1,  # Adaptive height
                            no_menus=True
                        ):
                            # X-axis (log scale)
                            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
                            
                            # Y-axis
                            y_axis = dpg.add_plot_axis(
                                dpg.mvYAxis, 
                                label="gamma [ohm·s·cm2]",
                                tag=f"y_axis_{data_type}_{category}_all"
                            )
                            
                            # Iterate through all files and add data
                            y_max_value = 0
                            for file_name in config.selected_files:
                                file_key = os.path.splitext(file_name)[0]
                                if file_key in config.store and 'EIS' in config.store[file_key]:
                                    data = config.store[file_key]['EIS']
                                    if data[f"tknv_{data_type}"] is not None:
                                        _add_series_to_plot(
                                            {
                                                'f': data[f"tknv_{data_type}"][category]['f'],
                                                'y': data[f"tknv_{data_type}"][category]['g']
                                            },
                                            y_axis,
                                            label=gui_utils.small_functions.string_abbreviation(file_key, 12, 12),
                                            is_line=True
                                        )
                                        if np.max(data[f"tknv_{data_type}"][category]['g']) > y_max_value:
                                            y_max_value = np.max(data[f"tknv_{data_type}"][category]['g'])

                            dpg.set_axis_limits(y_axis, 0, y_max_value * 1.1)
                            
                            # Add legend
                            dpg.add_plot_legend(
                                parent=f"plot_gamma_{data_type}_{category}_all",
                                location=dpg.mvPlot_Location_NorthEast  # Legend position at top-right
                            )

    print("---- DRT gamma distribution plots updated successfully.")
