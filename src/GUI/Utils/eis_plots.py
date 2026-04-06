import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils


def _has_zhit_data(eis_obj):
    return (
        hasattr(eis_obj, "zhit_data")
        and isinstance(eis_obj.zhit_data, dict)
        and eis_obj.zhit_data.get("f", None) is not None
    )


def _is_zhit_enabled(eis_obj):
    return bool(
        hasattr(eis_obj, "parameter")
        and isinstance(eis_obj.parameter, dict)
        and eis_obj.parameter.get("ZHIT", {}).get("enable", False)
    )


def _get_display_eis(config):
    if config.display_file in ([], None):
        return None
    key = os.path.splitext(config.display_file)[0]
    if key not in config.store or "EIS" not in config.store[key]:
        return None
    return config.store[key]["EIS"]


def _eis_from_selected(config):
    eis_list = []
    for file_name in config.selected_files:
        key = os.path.splitext(file_name)[0]
        if key in config.store and "EIS" in config.store[key]:
            eis_list.append((file_name, config.store[key]["EIS"]))
    return eis_list


def _ensure_or_clear_tab(tab_tag, tab_label, parent_tag):
    if dpg.does_item_exist(tab_tag):
        dpg.delete_item(tab_tag, children_only=True)
    else:
        with dpg.tab(label=tab_label, tag=tab_tag, parent=parent_tag):
            pass


def _ensure_tab_exists(tab_tag, tab_label, parent_tag):
    if not dpg.does_item_exist(parent_tag):
        return False
    if not dpg.does_item_exist(tab_tag):
        dpg.add_tab(label=tab_label, tag=tab_tag, parent=parent_tag)
    return True


def _ensure_tab_bar_exists(tab_bar_tag, parent_tag):
    if not dpg.does_item_exist(parent_tag):
        return False
    if not dpg.does_item_exist(tab_bar_tag):
        dpg.add_tab_bar(tag=tab_bar_tag, parent=parent_tag)
    return True


def _is_eis_all_tab_active():
    if not dpg.does_item_exist("tab_bar_eis_plot"):
        return False
    try:
        return dpg.get_value("tab_bar_eis_plot") == "tab_eis_plot_all"
    except Exception:
        return False


def _plot_single_three_views(parent_tag, data, data_category, compare_category):
    # Defensive cleanup for single-view refresh to avoid overlay/ghosting.
    for suffix in ("re", "im", "nyquist"):
        plot_tag = f"{parent_tag}_{data_category}_single_{suffix}"
        if dpg.does_item_exist(plot_tag):
            dpg.delete_item(plot_tag)

    with dpg.plot(
        tag=f"{parent_tag}_{data_category}_single_re",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm.cm2]")
        dpg.add_scatter_series(
            data[compare_category]["f"],
            data[compare_category]["Re"],
            parent=y_axis,
            label=compare_category.capitalize(),
        )
        dpg.add_line_series(
            data[data_category]["f"],
            data[data_category]["Re"],
            parent=y_axis,
            label=data_category.capitalize(),
        )
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_{data_category}_single_im",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(
            data[compare_category]["f"],
            -data[compare_category]["Im"],
            parent=y_axis,
            label=compare_category.capitalize(),
        )
        dpg.add_line_series(
            data[data_category]["f"],
            -data[data_category]["Im"],
            parent=y_axis,
            label=data_category.capitalize(),
        )
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_{data_category}_single_nyquist",
        width=-1,
        height=-1,
        no_menus=False,
        equal_aspects=True,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm.cm2]")
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(
            data[compare_category]["Re"],
            -data[compare_category]["Im"],
            parent=y_axis,
            label=compare_category.capitalize(),
        )
        dpg.add_line_series(
            data[data_category]["Re"],
            -data[data_category]["Im"],
            parent=y_axis,
            label=data_category.capitalize(),
        )
        dpg.add_plot_legend()


def _plot_all_three_views(parent_tag, eis_list, data_category, compare_category):
    dpg.add_plot(
        tag=f"{parent_tag}_{data_category}_all_re",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Frequency [Hz]",
        log_scale=True,
        parent=f"{parent_tag}_{data_category}_all_re",
    )
    y_axis_re = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="Z' [Ohm.cm2]",
        parent=f"{parent_tag}_{data_category}_all_re",
    )

    dpg.add_plot(
        tag=f"{parent_tag}_{data_category}_all_im",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Frequency [Hz]",
        log_scale=True,
        parent=f"{parent_tag}_{data_category}_all_im",
    )
    y_axis_im = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="-Z'' [Ohm.cm2]",
        parent=f"{parent_tag}_{data_category}_all_im",
    )

    dpg.add_plot(
        tag=f"{parent_tag}_{data_category}_all_nyquist",
        width=-1,
        height=-1,
        no_menus=False,
        equal_aspects=True,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Z' [Ohm.cm2]",
        parent=f"{parent_tag}_{data_category}_all_nyquist",
    )
    y_axis_ny = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="-Z'' [Ohm.cm2]",
        parent=f"{parent_tag}_{data_category}_all_nyquist",
    )

    for file_name, data in eis_list:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if data[data_category]["f"] is None:
            continue
        if data[compare_category]["f"] is None:
            continue

        tag_short = gui_utils.small_functions.string_abbreviation(file_name_no_ext, 12, 12)

        dpg.add_line_series(
            data[data_category]["f"],
            data[data_category]["Re"],
            parent=y_axis_re,
            label=f"{data_category}-{tag_short}",
        )
        dpg.add_line_series(
            data[data_category]["f"],
            -data[data_category]["Im"],
            parent=y_axis_im,
            label=f"{data_category}-{tag_short}",
        )
        dpg.add_line_series(
            data[data_category]["Re"],
            -data[data_category]["Im"],
            parent=y_axis_ny,
            label=f"{data_category}-{tag_short}",
        )

    dpg.add_plot_legend(parent=f"{parent_tag}_{data_category}_all_re")
    dpg.add_plot_legend(parent=f"{parent_tag}_{data_category}_all_im")
    dpg.add_plot_legend(parent=f"{parent_tag}_{data_category}_all_nyquist")


def _plot_single_modulus_phase_comparison(
    parent_tag,
    suffix,
    f_meas,
    z_mod_meas,
    phase_meas,
    f_fit,
    z_mod_fit,
    phase_fit,
    measured_label,
    fit_label,
):
    plot_tag = f"{parent_tag}_{suffix}_single_mod_phase"
    if dpg.does_item_exist(plot_tag):
        dpg.delete_item(plot_tag)

    with dpg.plot(
        tag=plot_tag,
        width=-1,
        height=-1,
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis_mod = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [Ohm.cm2]")
        y_axis_phase = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True)

        dpg.add_scatter_series(f_meas, z_mod_meas, parent=y_axis_mod, label=f"{measured_label}-|Z|")
        dpg.add_line_series(f_fit, z_mod_fit, parent=y_axis_mod, label=f"{fit_label}-|Z|")
        dpg.add_scatter_series(f_meas, phase_meas, parent=y_axis_phase, label=f"{measured_label}-Phase")
        dpg.add_line_series(f_fit, phase_fit, parent=y_axis_phase, label=f"{fit_label}-Phase")
        dpg.add_plot_legend()


def _plot_all_modulus_phase_comparison(
    parent_tag,
    suffix,
    data_source_list,
):
    dpg.add_plot(
        tag=f"{parent_tag}_{suffix}_all_mod_phase",
        width=-1,
        height=-1,
        no_menus=False,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Frequency [Hz]",
        log_scale=True,
        parent=f"{parent_tag}_{suffix}_all_mod_phase",
    )
    y_axis_mod = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="|Z| [Ohm.cm2]",
        parent=f"{parent_tag}_{suffix}_all_mod_phase",
    )
    y_axis_phase = dpg.add_plot_axis(
        dpg.mvYAxis2,
        label="Phase [deg]",
        opposite=True,
        parent=f"{parent_tag}_{suffix}_all_mod_phase",
    )

    for src in data_source_list:
        file_name_no_ext = src["name"]
        tag_short = gui_utils.small_functions.string_abbreviation(file_name_no_ext, 12, 12)

        dpg.add_scatter_series(src["f_meas"], src["z_mod_meas"], parent=y_axis_mod, label=f"Meas-|Z|-{tag_short}")
        dpg.add_line_series(src["f_fit"], src["z_mod_fit"], parent=y_axis_mod, label=f"Fit-|Z|-{tag_short}")
        dpg.add_scatter_series(src["f_meas"], src["phase_meas"], parent=y_axis_phase, label=f"Meas-Phase-{tag_short}")
        dpg.add_line_series(src["f_fit"], src["phase_fit"], parent=y_axis_phase, label=f"Fit-Phase-{tag_short}")

    dpg.add_plot_legend(parent=f"{parent_tag}_{suffix}_all_mod_phase")


def _get_zhit_phase_arrays(data):
    f = data["zhit_data"]["f"]
    phase_meas = np.zeros_like(f, dtype=float)
    phase_fit = np.zeros_like(f, dtype=float)

    if data["zhit_data"].get("phi_deg", None) is not None:
        phase_meas = -data["zhit_data"]["phi_deg"]
    if data["zhit_data"].get("phi_smooth_deg", None) is not None:
        phase_fit = -data["zhit_data"]["phi_smooth_deg"]
    else:
        phase_fit = phase_meas

    return phase_meas, phase_fit


def _get_zhit_smooth_reim(data):
    if not _has_zhit_data(data):
        return None

    f = data["zhit_data"].get("f", None)
    z_mod = data["zhit_data"].get("Z_mod_zhit", None)
    if f is None or z_mod is None:
        return None

    phi_deg = data["zhit_data"].get("phi_smooth_deg", None)
    if phi_deg is None:
        phi_deg = data["zhit_data"].get("phi_deg", None)
    if phi_deg is None:
        return None

    phi_rad = np.deg2rad(phi_deg)
    re = z_mod * np.cos(phi_rad)
    im = z_mod * np.sin(phi_rad)
    return f, re, im


def _get_zhit_residual_reim_on_raw(data):
    if not _has_zhit_data(data):
        return None, None, None
    if data["raw"]["f"] is None or data["raw"]["Z"] is None:
        return None, None, None

    zhit_smooth = _get_zhit_smooth_reim(data)
    if zhit_smooth is None:
        return None, None, None

    f_raw = np.asarray(data["raw"]["f"], dtype=float)
    re_raw = np.asarray(data["raw"]["Re"], dtype=float)
    im_raw = np.asarray(data["raw"]["Im"], dtype=float)
    z_abs_raw = np.abs(np.asarray(data["raw"]["Z"]))
    zhit_f = np.asarray(zhit_smooth[0], dtype=float)
    zhit_re = np.asarray(zhit_smooth[1], dtype=float)
    zhit_im = np.asarray(zhit_smooth[2], dtype=float)

    if f_raw.size == 0 or zhit_f.size == 0 or zhit_re.size == 0 or zhit_im.size == 0:
        return None, None, None

    zhit_sort_idx = np.argsort(zhit_f)
    zhit_f_sorted = zhit_f[zhit_sort_idx]
    zhit_re_sorted = zhit_re[zhit_sort_idx]
    zhit_im_sorted = zhit_im[zhit_sort_idx]
    logf_zhit = np.log10(zhit_f_sorted)

    f_min = np.nanmin(zhit_f_sorted)
    f_max = np.nanmax(zhit_f_sorted)
    valid_raw = np.isfinite(f_raw) & np.isfinite(re_raw) & np.isfinite(im_raw) & np.isfinite(z_abs_raw) & (z_abs_raw > 0)
    valid_raw &= (f_raw >= f_min) & (f_raw <= f_max)
    if not np.any(valid_raw):
        return None, None, None

    f_eval = f_raw[valid_raw]
    re_eval = re_raw[valid_raw]
    im_eval = im_raw[valid_raw]
    z_abs_eval = z_abs_raw[valid_raw]

    zhit_re_interp = np.interp(
        np.log10(f_eval),
        logf_zhit,
        zhit_re_sorted,
        left=np.nan,
        right=np.nan,
    )
    zhit_im_interp = np.interp(
        np.log10(f_eval),
        logf_zhit,
        zhit_im_sorted,
        left=np.nan,
        right=np.nan,
    )

    valid = np.isfinite(zhit_re_interp) & np.isfinite(zhit_im_interp) & np.isfinite(z_abs_eval) & (z_abs_eval > 0)
    if not np.any(valid):
        return None, None, None

    f_out = f_eval[valid]
    residual_re = (re_eval[valid] - zhit_re_interp[valid]) / z_abs_eval[valid] * 100
    residual_im = (im_eval[valid] - zhit_im_interp[valid]) / z_abs_eval[valid] * 100
    return f_out, residual_re, residual_im


def _plot_single_zhit_three_views(parent_tag, data):
    zhit_smooth = _get_zhit_smooth_reim(data)
    if zhit_smooth is None:
        return

    with dpg.plot(
        tag=f"{parent_tag}_zhit_smooth_single_re",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["f"], data["truncated"]["Re"], parent=y_axis, label="Truncated")
        dpg.add_line_series(zhit_smooth[0], zhit_smooth[1], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_zhit_smooth_single_im",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["f"], -data["truncated"]["Im"], parent=y_axis, label="Truncated")
        dpg.add_line_series(zhit_smooth[0], -zhit_smooth[2], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_zhit_smooth_single_nyquist",
        width=-1,
        height=-1,
        no_menus=False,
        equal_aspects=True,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm.cm2]")
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["Re"], -data["truncated"]["Im"], parent=y_axis, label="Truncated")
        dpg.add_line_series(zhit_smooth[1], -zhit_smooth[2], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()


def _plot_all_zhit_three_views(parent_tag, eis_list):
    dpg.add_plot(
        tag=f"{parent_tag}_zhit_smooth_all_re",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Frequency [Hz]",
        log_scale=True,
        parent=f"{parent_tag}_zhit_smooth_all_re",
    )
    y_axis_re = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="Z' [Ohm.cm2]",
        parent=f"{parent_tag}_zhit_smooth_all_re",
    )

    dpg.add_plot(
        tag=f"{parent_tag}_zhit_smooth_all_im",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Frequency [Hz]",
        log_scale=True,
        parent=f"{parent_tag}_zhit_smooth_all_im",
    )
    y_axis_im = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="-Z'' [Ohm.cm2]",
        parent=f"{parent_tag}_zhit_smooth_all_im",
    )

    dpg.add_plot(
        tag=f"{parent_tag}_zhit_smooth_all_nyquist",
        width=-1,
        height=-1,
        no_menus=False,
        equal_aspects=True,
    )
    dpg.add_plot_axis(
        dpg.mvXAxis,
        label="Z' [Ohm.cm2]",
        parent=f"{parent_tag}_zhit_smooth_all_nyquist",
    )
    y_axis_ny = dpg.add_plot_axis(
        dpg.mvYAxis,
        label="-Z'' [Ohm.cm2]",
        parent=f"{parent_tag}_zhit_smooth_all_nyquist",
    )

    for file_name, data in eis_list:
        if not _has_zhit_data(data):
            continue

        zhit_smooth = _get_zhit_smooth_reim(data)
        if zhit_smooth is None or data["truncated"]["f"] is None:
            continue

        file_name_no_ext = os.path.splitext(file_name)[0]
        tag_short = gui_utils.small_functions.string_abbreviation(file_name_no_ext, 12, 12)

        dpg.add_scatter_series(
            data["truncated"]["f"],
            data["truncated"]["Re"],
            parent=y_axis_re,
            label=f"Truncated-{tag_short}",
        )
        dpg.add_line_series(
            zhit_smooth[0],
            zhit_smooth[1],
            parent=y_axis_re,
            label=f"ZHIT-{tag_short}",
        )

        dpg.add_scatter_series(
            data["truncated"]["f"],
            -data["truncated"]["Im"],
            parent=y_axis_im,
            label=f"Truncated-{tag_short}",
        )
        dpg.add_line_series(
            zhit_smooth[0],
            -zhit_smooth[2],
            parent=y_axis_im,
            label=f"ZHIT-{tag_short}",
        )

        dpg.add_scatter_series(
            data["truncated"]["Re"],
            -data["truncated"]["Im"],
            parent=y_axis_ny,
            label=f"Truncated-{tag_short}",
        )
        dpg.add_line_series(
            zhit_smooth[1],
            -zhit_smooth[2],
            parent=y_axis_ny,
            label=f"ZHIT-{tag_short}",
        )

    dpg.add_plot_legend(parent=f"{parent_tag}_zhit_smooth_all_re")
    dpg.add_plot_legend(parent=f"{parent_tag}_zhit_smooth_all_im")
    dpg.add_plot_legend(parent=f"{parent_tag}_zhit_smooth_all_nyquist")


def _plot_single_comparison_smooth(parent_tag, data, has_zhit_data):
    zhit_smooth = _get_zhit_smooth_reim(data) if has_zhit_data else None

    with dpg.plot(
        tag=f"{parent_tag}_smooth_compare_re",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Z' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["f"], data["truncated"]["Re"], parent=y_axis, label="Truncated")
        dpg.add_line_series(data["smooth"]["f"], data["smooth"]["Re"], parent=y_axis, label="KK smooth")
        if zhit_smooth is not None:
            dpg.add_line_series(zhit_smooth[0], zhit_smooth[1], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_smooth_compare_im",
        width=-1,
        height=int(dpg.get_viewport_height() * 0.25),
        no_menus=False,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["f"], -data["truncated"]["Im"], parent=y_axis, label="Truncated")
        dpg.add_line_series(data["smooth"]["f"], -data["smooth"]["Im"], parent=y_axis, label="KK smooth")
        if zhit_smooth is not None:
            dpg.add_line_series(zhit_smooth[0], -zhit_smooth[2], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()

    with dpg.plot(
        tag=f"{parent_tag}_smooth_compare_nyquist",
        width=-1,
        height=-1,
        no_menus=False,
        equal_aspects=True,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label="Z' [Ohm.cm2]")
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="-Z'' [Ohm.cm2]")
        dpg.add_scatter_series(data["truncated"]["Re"], -data["truncated"]["Im"], parent=y_axis, label="Truncated")
        dpg.add_line_series(data["smooth"]["Re"], -data["smooth"]["Im"], parent=y_axis, label="KK smooth")
        if zhit_smooth is not None:
            dpg.add_line_series(zhit_smooth[1], -zhit_smooth[2], parent=y_axis, label="ZHIT smooth")
        dpg.add_plot_legend()


def _render_kk_single(parent_tag, data):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_tab_bar_exists(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_residual",
        tab_label="Residual",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_lccorrect",
        tab_label="LCcorrect",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_smooth",
        tab_label="Smooth",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_extrapolation",
        tab_label="Extrapolation",
        parent_tag=subtab_tag,
    )

    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        kk_z = data["KK_data"]["Re"] + 1j * data["KK_data"]["Im"]
        with dpg.plot(
            tag=f"{parent_tag}_plot_residual",
            width=-1,
            height=int(dpg.get_viewport_height() * 0.25),
            no_menus=False,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="KK Residual [%]")
            dpg.add_scatter_series(data["KK_data"]["f"], data["KK_data"]["delta_Re_kk"], parent=y_axis, label="Re")
            dpg.add_scatter_series(data["KK_data"]["f"], data["KK_data"]["delta_Im_kk"], parent=y_axis, label="Im")
            dpg.add_plot_legend()

        _plot_single_modulus_phase_comparison(
            parent_tag=parent_tag,
            suffix="kk_residual_cmp",
            f_meas=data["raw"]["f"],
            z_mod_meas=np.abs(data["raw"]["Z"]),
            phase_meas=-np.degrees(np.angle(data["raw"]["Z"])),
            f_fit=data["KK_data"]["f"],
            z_mod_fit=np.abs(kk_z),
            phase_fit=-np.degrees(np.angle(kk_z)),
            measured_label="Measured",
            fit_label="KK-fit",
        )

    with dpg.group(parent=f"{parent_tag}_tab_lccorrect"):
        _plot_single_three_views(parent_tag, data, "LCcorrect", "truncated")

    with dpg.group(parent=f"{parent_tag}_tab_smooth"):
        _plot_single_three_views(parent_tag, data, "smooth", "truncated")

    with dpg.group(parent=f"{parent_tag}_tab_extrapolation"):
        _plot_single_three_views(parent_tag, data, "extrapolation", "truncated")


def _render_kk_all(parent_tag, eis_list):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_tab_bar_exists(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_residual",
        tab_label="Residual",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_lccorrect",
        tab_label="LCcorrect",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_smooth",
        tab_label="Smooth",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_extrapolation",
        tab_label="Extrapolation",
        parent_tag=subtab_tag,
    )

    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        dpg.add_plot(
            tag=f"{parent_tag}_plot_residual",
            width=-1,
            height=int(dpg.get_viewport_height() * 0.25),
            no_menus=False,
        )
        dpg.add_plot_axis(
            dpg.mvXAxis,
            label="Frequency [Hz]",
            log_scale=True,
            parent=f"{parent_tag}_plot_residual",
        )
        y_axis = dpg.add_plot_axis(
            dpg.mvYAxis,
            label="KK Residual [%]",
            parent=f"{parent_tag}_plot_residual",
        )
        for file_name, data in eis_list:
            file_name_no_ext = os.path.splitext(file_name)[0]
            if data["KK_data"]["f"] is None:
                continue
            dpg.add_scatter_series(
                data["KK_data"]["f"],
                data["KK_data"]["delta_Re_kk"],
                parent=y_axis,
                label=gui_utils.small_functions.string_abbreviation(f"Re-{file_name_no_ext}", 16, 12),
            )
            dpg.add_scatter_series(
                data["KK_data"]["f"],
                data["KK_data"]["delta_Im_kk"],
                parent=y_axis,
                label=gui_utils.small_functions.string_abbreviation(f"Im-{file_name_no_ext}", 16, 12),
            )
        dpg.add_plot_legend(parent=f"{parent_tag}_plot_residual")

        kk_cmp_sources = []
        for file_name, data in eis_list:
            file_name_no_ext = os.path.splitext(file_name)[0]
            if data["KK_data"]["f"] is None or data["raw"]["f"] is None:
                continue
            kk_z = data["KK_data"]["Re"] + 1j * data["KK_data"]["Im"]
            kk_cmp_sources.append(
                {
                    "name": file_name_no_ext,
                    "f_meas": data["raw"]["f"],
                    "z_mod_meas": np.abs(data["raw"]["Z"]),
                    "phase_meas": -np.degrees(np.angle(data["raw"]["Z"])),
                    "f_fit": data["KK_data"]["f"],
                    "z_mod_fit": np.abs(kk_z),
                    "phase_fit": -np.degrees(np.angle(kk_z)),
                }
            )
        if kk_cmp_sources:
            _plot_all_modulus_phase_comparison(
                parent_tag=parent_tag,
                suffix="kk_residual_cmp",
                data_source_list=kk_cmp_sources,
            )

    with dpg.group(parent=f"{parent_tag}_tab_lccorrect"):
        _plot_all_three_views(parent_tag, eis_list, "LCcorrect", "truncated")

    with dpg.group(parent=f"{parent_tag}_tab_smooth"):
        _plot_all_three_views(parent_tag, eis_list, "smooth", "truncated")

    with dpg.group(parent=f"{parent_tag}_tab_extrapolation"):
        _plot_all_three_views(parent_tag, eis_list, "extrapolation", "truncated")


def _render_zhit_single(parent_tag, data):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_tab_bar_exists(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_residual",
        tab_label="Residual",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_smooth",
        tab_label="Smooth",
        parent_tag=subtab_tag,
    )

    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        _, phase_fit = _get_zhit_phase_arrays(data)
        raw_res_f, raw_res_re, raw_res_im = _get_zhit_residual_reim_on_raw(data)
        with dpg.plot(
            tag=f"{parent_tag}_plot_residual",
            width=-1,
            height=int(dpg.get_viewport_height() * 0.25),
            no_menus=False,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]")
            if raw_res_f is not None:
                dpg.add_scatter_series(raw_res_f, raw_res_re, parent=y_axis, label="ZHIT Re")
                dpg.add_scatter_series(raw_res_f, raw_res_im, parent=y_axis, label="ZHIT Im")
            dpg.add_plot_legend()

        _plot_single_modulus_phase_comparison(
            parent_tag=parent_tag,
            suffix="zhit_residual_cmp",
            f_meas=data["raw"]["f"],
            z_mod_meas=np.abs(data["raw"]["Z"]),
            phase_meas=-np.degrees(np.angle(data["raw"]["Z"])),
            f_fit=data["zhit_data"]["f"],
            z_mod_fit=data["zhit_data"]["Z_mod_zhit"],
            phase_fit=phase_fit,
            measured_label="Measured",
            fit_label="ZHIT-fit",
        )

    with dpg.group(parent=f"{parent_tag}_tab_smooth"):
        _plot_single_zhit_three_views(parent_tag, data)


def _render_zhit_all(parent_tag, eis_list):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_tab_bar_exists(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_residual",
        tab_label="Residual",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_smooth",
        tab_label="Smooth",
        parent_tag=subtab_tag,
    )

    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        dpg.add_plot(
            tag=f"{parent_tag}_plot_residual",
            width=-1,
            height=int(dpg.get_viewport_height() * 0.25),
            no_menus=False,
        )
        dpg.add_plot_axis(
            dpg.mvXAxis,
            label="Frequency [Hz]",
            log_scale=True,
            parent=f"{parent_tag}_plot_residual",
        )
        y_axis = dpg.add_plot_axis(
            dpg.mvYAxis,
            label="Residual [%]",
            parent=f"{parent_tag}_plot_residual",
        )
        for file_name, data in eis_list:
            file_name_no_ext = os.path.splitext(file_name)[0]
            if not _has_zhit_data(data):
                continue
            raw_res_f, raw_res_re, raw_res_im = _get_zhit_residual_reim_on_raw(data)
            if raw_res_f is None:
                continue
            dpg.add_scatter_series(
                raw_res_f,
                raw_res_re,
                parent=y_axis,
                label=gui_utils.small_functions.string_abbreviation(f"ZHIT-Re-{file_name_no_ext}", 16, 12),
            )
            dpg.add_scatter_series(
                raw_res_f,
                raw_res_im,
                parent=y_axis,
                label=gui_utils.small_functions.string_abbreviation(f"ZHIT-Im-{file_name_no_ext}", 16, 12),
            )
        dpg.add_plot_legend(parent=f"{parent_tag}_plot_residual")

        zhit_cmp_sources = []
        for file_name, data in eis_list:
            file_name_no_ext = os.path.splitext(file_name)[0]
            if not _has_zhit_data(data):
                continue
            _, phase_fit = _get_zhit_phase_arrays(data)
            zhit_cmp_sources.append(
                {
                    "name": file_name_no_ext,
                    "f_meas": data["raw"]["f"],
                    "z_mod_meas": np.abs(data["raw"]["Z"]),
                    "phase_meas": -np.degrees(np.angle(data["raw"]["Z"])),
                    "f_fit": data["zhit_data"]["f"],
                    "z_mod_fit": data["zhit_data"]["Z_mod_zhit"],
                    "phase_fit": phase_fit,
                }
            )
        if zhit_cmp_sources:
            _plot_all_modulus_phase_comparison(
                parent_tag=parent_tag,
                suffix="zhit_residual_cmp",
                data_source_list=zhit_cmp_sources,
            )

    with dpg.group(parent=f"{parent_tag}_tab_smooth"):
        _plot_all_zhit_three_views(parent_tag, eis_list)


def _render_comparison_single(parent_tag, data, has_zhit_data):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_tab_bar_exists(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_residual",
        tab_label="Residual",
        parent_tag=subtab_tag,
    )
    _ensure_or_clear_tab(
        tab_tag=f"{parent_tag}_tab_smooth",
        tab_label="Smooth",
        parent_tag=subtab_tag,
    )

    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        with dpg.plot(
            tag=f"{parent_tag}_plot_residual",
            width=-1,
            height=int(dpg.get_viewport_height() * 0.25),
            no_menus=False,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Residual [%]")
            dpg.add_scatter_series(
                data["KK_data"]["f"],
                data["KK_data"]["delta_Re_kk"],
                parent=y_axis,
                label="KK Re",
            )
            dpg.add_scatter_series(
                data["KK_data"]["f"],
                data["KK_data"]["delta_Im_kk"],
                parent=y_axis,
                label="KK Im",
            )
            if has_zhit_data:
                raw_res_f, raw_res_re, raw_res_im = _get_zhit_residual_reim_on_raw(data)
                if raw_res_f is not None:
                    dpg.add_scatter_series(
                        raw_res_f,
                        raw_res_re,
                        parent=y_axis,
                        label="ZHIT Re",
                    )
                    dpg.add_scatter_series(
                        raw_res_f,
                        raw_res_im,
                        parent=y_axis,
                        label="ZHIT Im",
                    )
            dpg.add_plot_legend()

        kk_z = data["KK_data"]["Re"] + 1j * data["KK_data"]["Im"]
        with dpg.plot(
            tag=f"{parent_tag}_plot_mod_phase_fit",
            width=-1,
            height=-1,
            no_menus=False,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label="Frequency [Hz]", log_scale=True)
            y_axis_mod = dpg.add_plot_axis(dpg.mvYAxis, label="|Z| [Ohm.cm2]")
            y_axis_phase = dpg.add_plot_axis(dpg.mvYAxis2, label="Phase [deg]", opposite=True)

            dpg.add_scatter_series(
                data["raw"]["f"],
                np.abs(data["raw"]["Z"]),
                parent=y_axis_mod,
                label="Measured-|Z|",
            )
            dpg.add_line_series(
                data["KK_data"]["f"],
                np.abs(kk_z),
                parent=y_axis_mod,
                label="KK-fit-|Z|",
            )
            dpg.add_scatter_series(
                data["raw"]["f"],
                -np.degrees(np.angle(data["raw"]["Z"])),
                parent=y_axis_phase,
                label="Measured-Phase",
            )
            dpg.add_line_series(
                data["KK_data"]["f"],
                -np.degrees(np.angle(kk_z)),
                parent=y_axis_phase,
                label="KK-fit-Phase",
            )

            if has_zhit_data:
                _, phase_fit = _get_zhit_phase_arrays(data)
                dpg.add_line_series(
                    data["zhit_data"]["f"],
                    data["zhit_data"]["Z_mod_zhit"],
                    parent=y_axis_mod,
                    label="ZHIT-fit-|Z|",
                )
                dpg.add_line_series(
                    data["zhit_data"]["f"],
                    phase_fit,
                    parent=y_axis_phase,
                    label="ZHIT-fit-Phase",
                )

            dpg.add_plot_legend()

    with dpg.group(parent=f"{parent_tag}_tab_smooth"):
        _plot_single_comparison_smooth(parent_tag, data, has_zhit_data)


def update_single_plots(config):
    print("-- EIS data single plots updating...")
    if not dpg.does_item_exist("tab_bar_eis_plot_single"):
        print("---- Skipped: tab_bar_eis_plot_single not found.")
        return

    data = _get_display_eis(config)
    has_valid_data = data is not None and data["truncated"]["f"] is not None
    has_zhit_data = data is not None and _has_zhit_data(data)
    zhit_enabled = data is not None and _is_zhit_enabled(data)

    if not has_valid_data:
        for tag in [
            "tab_eis_truncated_plot_single",
            "tab_eis_kk_plot_single",
            "tab_eis_zhit_plot_single",
            "tab_eis_comparison_plot_single",
        ]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag, children_only=True)
        print("---- Continue. The specified file does not exist or not processed.")
        return

    _ensure_or_clear_tab("tab_eis_truncated_plot_single", "Truncated", "tab_bar_eis_plot_single")
    _ensure_or_clear_tab("tab_eis_kk_plot_single", "KK", "tab_bar_eis_plot_single")

    if has_zhit_data:
        _ensure_tab_exists("tab_eis_zhit_plot_single", "ZHIT", "tab_bar_eis_plot_single")
    elif dpg.does_item_exist("tab_eis_zhit_plot_single"):
        dpg.delete_item("tab_eis_zhit_plot_single")

    if zhit_enabled:
        _ensure_tab_exists("tab_eis_comparison_plot_single", "Comparison", "tab_bar_eis_plot_single")
    elif dpg.does_item_exist("tab_eis_comparison_plot_single"):
        dpg.delete_item("tab_eis_comparison_plot_single")

    with dpg.group(parent="tab_eis_truncated_plot_single"):
        _plot_single_three_views("tab_eis_truncated_plot_single", data, "truncated", "raw")

    with dpg.group(parent="tab_eis_kk_plot_single"):
        _render_kk_single("tab_eis_kk_plot_single", data)

    if has_zhit_data:
        with dpg.group(parent="tab_eis_zhit_plot_single"):
            _render_zhit_single("tab_eis_zhit_plot_single", data)

    if zhit_enabled:
        with dpg.group(parent="tab_eis_comparison_plot_single"):
            _render_comparison_single("tab_eis_comparison_plot_single", data, has_zhit_data)

    print("---- EIS data single plots updated successfully.")


def update_all_plots(config):
    print("-- EIS data all plots updating...")
    if not dpg.does_item_exist("tab_bar_eis_plot_all"):
        print("---- Skipped: tab_bar_eis_plot_all not found.")
        return

    eis_list = _eis_from_selected(config)
    has_valid_data = any(eis_obj["truncated"]["f"] is not None for _, eis_obj in eis_list)
    has_any_zhit_data = any(_has_zhit_data(eis_obj) for _, eis_obj in eis_list)

    if not has_valid_data:
        for tag in ["tab_eis_truncated_plot_all", "tab_eis_kk_plot_all", "tab_eis_zhit_plot_all"]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag, children_only=True)
        print("---- Continue. No processed EIS data in selected files.")
        return

    _ensure_or_clear_tab("tab_eis_truncated_plot_all", "Truncated", "tab_bar_eis_plot_all")
    _ensure_or_clear_tab("tab_eis_kk_plot_all", "KK", "tab_bar_eis_plot_all")

    if has_any_zhit_data:
        _ensure_or_clear_tab("tab_eis_zhit_plot_all", "ZHIT", "tab_bar_eis_plot_all")
    elif dpg.does_item_exist("tab_eis_zhit_plot_all"):
        dpg.delete_item("tab_eis_zhit_plot_all")

    with dpg.group(parent="tab_eis_truncated_plot_all"):
        _plot_all_three_views("tab_eis_truncated_plot_all", eis_list, "truncated", "raw")

    with dpg.group(parent="tab_eis_kk_plot_all"):
        _render_kk_all("tab_eis_kk_plot_all", eis_list)

    if has_any_zhit_data:
        with dpg.group(parent="tab_eis_zhit_plot_all"):
            _render_zhit_all("tab_eis_zhit_plot_all", eis_list)

    print("---- EIS data all plots updated successfully.")
