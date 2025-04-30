import os
import numpy as np
import dearpygui.dearpygui as dpg

def _ensure_contiguous(data):
    """确保NumPy数组是C连续的，并处理NaN值"""
    if isinstance(data, dict):
        return {k: np.ascontiguousarray(v) if isinstance(v, np.ndarray) else v for k, v in data.items()}
    return np.ascontiguousarray(data)

def _create_plot_with_axes(parent_tag, width, height, x_label, y_label, log_x=False):
    """创建带有坐标轴的绘图区域"""
    with dpg.plot(tag=parent_tag, width=width, height=height, no_menus=True):
        dpg.add_plot_axis(dpg.mvXAxis, label=x_label, log_scale=log_x)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)
        return y_axis

def _add_series_to_plot(plot_data, y_axis, label, is_line=True):
    """添加线或散点序列到绘图"""
    x_data = _ensure_contiguous(plot_data['f'])
    y_data = _ensure_contiguous(plot_data['y'])
    if is_line:
        dpg.add_line_series(x_data, y_data, parent=y_axis, label=label)
    else:
        dpg.add_scatter_series(x_data, y_data, parent=y_axis, label=label)

def _update_bode_plots(data, parent_tag, data_category):
    """更新Bode图（Re和Im）"""
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
    """更新Nyquist图"""
    y_axis = _create_plot_with_axes(
        f"{parent_tag}_ReIm", -1, -1,
        "Z' [Ohm·cm2]", "-Z'' [Ohm·cm2]"
    )
    _add_series_to_plot({'f': data.truncated['Re'], 'y': -data.truncated['Im']}, y_axis, f"{data_category}_truncated", False)
    _add_series_to_plot({'f': data.smooth['Re'], 'y': -data.smooth['Im']}, y_axis, f"{data_category}_KK_smooth")
    _add_series_to_plot({'f': data.tknv_truncated[data_category]['Re'], 'y': -data.tknv_truncated[data_category]['Im']}, y_axis, f"{data_category}_DRT_smooth")
    dpg.add_plot_legend(parent=f"{parent_tag}_ReIm")

def update_single_plots(config):
    """更新单文件DRT绘图"""
    print("-- Updating DRT single plots...")
    if not config.display_file or os.path.splitext(config.display_file)[0] not in config.store:
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
                        for category in ["ReIm", "Re", "Im"]:
                            dpg.set_axis_limits(y_axis, 0, np.max(data[f"tknv_{data_type}"][category]['g']) * 1.1)
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
