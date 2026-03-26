import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def _has_zhit_tknv(data):
    return (
        hasattr(data, "tknv_zhit")
        and isinstance(data.tknv_zhit, dict)
        and data.tknv_zhit.get("Re", None) is not None
        and data.tknv_zhit.get("Im", None) is not None
        and data.tknv_zhit.get("ReIm", None) is not None
    )


def _get_zhit_smooth_eis(data):
    if not hasattr(data, "zhit_data") or data.zhit_data.get("f", None) is None:
        return None

    f = data.zhit_data.get("f", None)
    z_mod = data.zhit_data.get("Z_mod_zhit", None)
    phi_deg = data.zhit_data.get("phi_smooth_deg", None)
    if phi_deg is None:
        phi_deg = data.zhit_data.get("phi_deg", None)
    if f is None or z_mod is None or phi_deg is None:
        return None

    f = np.asarray(f, dtype=float)
    z_mod = np.asarray(z_mod, dtype=float)
    phi_deg = np.asarray(phi_deg, dtype=float)
    valid = np.isfinite(f) & np.isfinite(z_mod) & np.isfinite(phi_deg) & (f > 0)
    if not np.any(valid):
        return None

    f = f[valid]
    z_mod = z_mod[valid]
    phi_deg = phi_deg[valid]

    phi_rad = np.deg2rad(phi_deg)
    re = z_mod * np.cos(phi_rad)
    im = z_mod * np.sin(phi_rad)
    z = re + 1j * im

    return {
        "f": f,
        "Re": re,
        "Im": im,
        "Z": z,
    }


def _ensure_or_clear_tab(tab_tag, tab_label, parent_tag):
    if not dpg.does_item_exist(parent_tag):
        print(f"-- Warning: parent tab bar '{parent_tag}' missing for tab '{tab_tag}'.")
        return False

    if dpg.does_item_exist(tab_tag):
        dpg.delete_item(tab_tag, children_only=True)
        return True

    dpg.add_tab(label=tab_label, tag=tab_tag, parent=parent_tag)
    return True


def _ensure_tab_exists(tab_tag, tab_label, parent_tag):
    if not dpg.does_item_exist(parent_tag):
        print(f"-- Warning: parent tab bar '{parent_tag}' missing for tab '{tab_tag}'.")
        return False

    if not dpg.does_item_exist(tab_tag):
        dpg.add_tab(label=tab_label, tag=tab_tag, parent=parent_tag)
    return True


def _ensure_or_reset_tab_bar(tab_bar_tag, parent_tag):
    if not dpg.does_item_exist(parent_tag):
        print(f"-- Warning: parent tab '{parent_tag}' missing for tab bar '{tab_bar_tag}'.")
        return False

    if not dpg.does_item_exist(tab_bar_tag):
        dpg.add_tab_bar(tag=tab_bar_tag, parent=parent_tag)
    return True

def _create_plot_with_axes(parent_tag, width, height, x_label, y_label, log_x=False):
    """Create a plot area with axes."""
    equal_aspects_switch = True if "Z'" in x_label and "Z''" in y_label else False
    with dpg.plot(tag=parent_tag, width=width, height=height, no_menus=False, equal_aspects=equal_aspects_switch):
        dpg.add_plot_axis(dpg.mvXAxis, label=x_label, log_scale=log_x)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label=y_label)
        return y_axis

def _add_series_to_plot(plot_data, y_axis, label, is_line=True):
    """Add a line or scatter series to the plot."""
    x_data, y_data = _prepare_xy(plot_data['f'], plot_data['y'], require_positive_x=True)
    if x_data is None:
        print(f"-- Warning: Skip invalid series '{label}'.")
        return
    if dpg.get_value('check_box_drt_tau'):
        x_data = 1/(2*np.pi*x_data)  # Convert frequency to tau if the button is active
        x_data, y_data = _prepare_xy(x_data, y_data, require_positive_x=True)
        if x_data is None:
            print(f"-- Warning: Skip invalid tau series '{label}'.")
            return
    if is_line:
        dpg.add_line_series(x_data, y_data, parent=y_axis, label=label)
    else:
        dpg.add_scatter_series(x_data, y_data, parent=y_axis, label=label)


def _prepare_xy(x_data, y_data, require_positive_x=False):
    try:
        x_arr = np.asarray(x_data, dtype=float).reshape(-1)
        y_arr = np.asarray(y_data, dtype=float).reshape(-1)
    except Exception:
        return None, None

    n = min(len(x_arr), len(y_arr))
    if n < 2:
        return None, None

    x_arr = x_arr[:n]
    y_arr = y_arr[:n]

    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    if require_positive_x:
        valid &= x_arr > 0
    if np.count_nonzero(valid) < 2:
        return None, None

    return np.ascontiguousarray(x_arr[valid]), np.ascontiguousarray(y_arr[valid])


def _safe_add_xy_series(y_axis, x_data, y_data, label, is_line=True, require_positive_x=False):
    x_arr, y_arr = _prepare_xy(x_data, y_data, require_positive_x=require_positive_x)
    if x_arr is None:
        print(f"-- Warning: Skip invalid XY series '{label}'.")
        return
    if is_line:
        dpg.add_line_series(x_arr, y_arr, parent=y_axis, label=label)
    else:
        dpg.add_scatter_series(x_arr, y_arr, parent=y_axis, label=label)


def _plot_three_views_with_drt(data, parent_tag, data_category, measured, measured_label, smooth, smooth_label, drt_data, extra_series=None):
    y_axis_re = _create_plot_with_axes(
        f"{parent_tag}_Re", -1, int(dpg.get_viewport_height() * 0.25),
        "Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]", "Z' [Ohm·cm2]", log_x=True
    )
    _add_series_to_plot({'f': measured['f'], 'y': measured['Re']}, y_axis_re, f"{data_category}_{measured_label}", False)
    _add_series_to_plot({'f': smooth['f'], 'y': smooth['Re']}, y_axis_re, f"{data_category}_{smooth_label}")
    if extra_series is not None:
        extra_label = extra_series.get('label', 'extra')
        extra_smooth = extra_series.get('smooth', None)
        extra_drt = extra_series.get('drt', None)
        if extra_smooth is not None:
            _add_series_to_plot({'f': extra_smooth['f'], 'y': extra_smooth['Re']}, y_axis_re, f"{data_category}_{extra_label}_smooth")
        if isinstance(extra_drt, dict) and data_category in extra_drt:
            _add_series_to_plot({'f': extra_drt[data_category]['f'], 'y': extra_drt[data_category]['Re']}, y_axis_re, f"{data_category}_{extra_label}_DRT")
    _add_series_to_plot({'f': drt_data[data_category]['f'], 'y': drt_data[data_category]['Re']}, y_axis_re, f"{data_category}_DRT")
    dpg.add_plot_legend(parent=f"{parent_tag}_Re")

    y_axis_im = _create_plot_with_axes(
        f"{parent_tag}_Im", -1, int(dpg.get_viewport_height() * 0.25),
        "Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]", "-Z'' [Ohm·cm2]", log_x=True
    )
    _add_series_to_plot({'f': measured['f'], 'y': -measured['Im']}, y_axis_im, f"{data_category}_{measured_label}", False)
    _add_series_to_plot({'f': smooth['f'], 'y': -smooth['Im']}, y_axis_im, f"{data_category}_{smooth_label}")
    if extra_series is not None:
        extra_label = extra_series.get('label', 'extra')
        extra_smooth = extra_series.get('smooth', None)
        extra_drt = extra_series.get('drt', None)
        if extra_smooth is not None:
            _add_series_to_plot({'f': extra_smooth['f'], 'y': -extra_smooth['Im']}, y_axis_im, f"{data_category}_{extra_label}_smooth")
        if isinstance(extra_drt, dict) and data_category in extra_drt:
            _add_series_to_plot({'f': extra_drt[data_category]['f'], 'y': -extra_drt[data_category]['Im']}, y_axis_im, f"{data_category}_{extra_label}_DRT")
    _add_series_to_plot({'f': drt_data[data_category]['f'], 'y': -drt_data[data_category]['Im']}, y_axis_im, f"{data_category}_DRT")
    dpg.add_plot_legend(parent=f"{parent_tag}_Im")

    y_axis = _create_plot_with_axes(
        f"{parent_tag}_ReIm", -1, -1,
        "Z' [Ohm·cm2]", "-Z'' [Ohm·cm2]"
    )
    _safe_add_xy_series(
        y_axis,
        measured['Re'],
        -np.asarray(measured['Im']),
        f"{data_category}_{measured_label}",
        is_line=False,
        require_positive_x=False,
    )
    _safe_add_xy_series(
        y_axis,
        smooth['Re'],
        -np.asarray(smooth['Im']),
        f"{data_category}_{smooth_label}",
        is_line=True,
        require_positive_x=False,
    )
    if extra_series is not None:
        extra_label = extra_series.get('label', 'extra')
        extra_smooth = extra_series.get('smooth', None)
        extra_drt = extra_series.get('drt', None)
        if extra_smooth is not None:
            _safe_add_xy_series(
                y_axis,
                extra_smooth['Re'],
                -np.asarray(extra_smooth['Im']),
                f"{data_category}_{extra_label}_smooth",
                is_line=True,
                require_positive_x=False,
            )
        if isinstance(extra_drt, dict) and data_category in extra_drt:
            _safe_add_xy_series(
                y_axis,
                extra_drt[data_category]['Re'],
                -np.asarray(extra_drt[data_category]['Im']),
                f"{data_category}_{extra_label}_DRT",
                is_line=True,
                require_positive_x=False,
            )
    _safe_add_xy_series(
        y_axis,
        drt_data[data_category]['Re'],
        -np.asarray(drt_data[data_category]['Im']),
        f"{data_category}_DRT",
        is_line=True,
        require_positive_x=False,
    )
    dpg.add_plot_legend(parent=f"{parent_tag}_ReIm")


def _compute_residual_series(f_ref, re_ref, im_ref, z_ref, f_fit, re_fit, im_fit):
    f_ref = np.asarray(f_ref, dtype=float)
    re_ref = np.asarray(re_ref, dtype=float)
    im_ref = np.asarray(im_ref, dtype=float)
    z_abs_ref = np.abs(np.asarray(z_ref))
    f_fit = np.asarray(f_fit, dtype=float)
    re_fit = np.asarray(re_fit, dtype=float)
    im_fit = np.asarray(im_fit, dtype=float)

    fit_sort = np.argsort(f_fit)
    f_fit_sorted = f_fit[fit_sort]
    re_fit_sorted = re_fit[fit_sort]
    im_fit_sorted = im_fit[fit_sort]

    f_min = np.nanmin(f_fit_sorted)
    f_max = np.nanmax(f_fit_sorted)
    valid = np.isfinite(f_ref) & np.isfinite(re_ref) & np.isfinite(im_ref) & np.isfinite(z_abs_ref) & (z_abs_ref > 0)
    valid &= (f_ref >= f_min) & (f_ref <= f_max)
    if not np.any(valid):
        return None, None, None

    f_eval = f_ref[valid]
    re_eval = re_ref[valid]
    im_eval = im_ref[valid]
    z_abs_eval = z_abs_ref[valid]

    re_interp = np.interp(np.log10(f_eval), np.log10(f_fit_sorted), re_fit_sorted)
    im_interp = np.interp(np.log10(f_eval), np.log10(f_fit_sorted), im_fit_sorted)

    residual_re = (re_eval - re_interp) / z_abs_eval * 100
    residual_im = (im_eval - im_interp) / z_abs_eval * 100
    return f_eval, residual_re, residual_im


def _plot_residuals(parent_tag, ref_data, drt_data, extra_drt_data=None, extra_label="ZHIT", kk_smooth_data=None):
    y_axis_re = _create_plot_with_axes(
        f"{parent_tag}_ReIm_residual", -1, int(dpg.get_viewport_height() * 0.25),
        "Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]", "Residual [%]", log_x=True
    )

    f_eval, residual_re, residual_im = _compute_residual_series(
        ref_data['f'],
        ref_data['Re'],
        ref_data['Im'],
        ref_data['Z'],
        drt_data['ReIm']['f'],
        drt_data['ReIm']['Re'],
        drt_data['ReIm']['Im'],
    )
    if f_eval is None:
        print("-- Warning: Failed to build ReIm residual series due to invalid overlap.")
    else:
        _add_series_to_plot({'f': f_eval, 'y': residual_re}, y_axis_re, "DRT_ReIm_Re", False)
        _add_series_to_plot({'f': f_eval, 'y': residual_im}, y_axis_re, "DRT_ReIm_Im", False)
    if isinstance(extra_drt_data, dict) and extra_drt_data.get('ReIm', None) is not None:
        f_eval_extra, residual_re_extra, residual_im_extra = _compute_residual_series(
            ref_data['f'],
            ref_data['Re'],
            ref_data['Im'],
            ref_data['Z'],
            extra_drt_data['ReIm']['f'],
            extra_drt_data['ReIm']['Re'],
            extra_drt_data['ReIm']['Im'],
        )
        if f_eval_extra is not None:
            _add_series_to_plot({'f': f_eval_extra, 'y': residual_re_extra}, y_axis_re, f"{extra_label}_ReIm_Re", False)
            _add_series_to_plot({'f': f_eval_extra, 'y': residual_im_extra}, y_axis_re, f"{extra_label}_ReIm_Im", False)
    if isinstance(kk_smooth_data, dict) and kk_smooth_data.get('f', None) is not None:
        f_eval_kk, residual_re_kk, residual_im_kk = _compute_residual_series(
            ref_data['f'],
            ref_data['Re'],
            ref_data['Im'],
            ref_data['Z'],
            kk_smooth_data['f'],
            kk_smooth_data['Re'],
            kk_smooth_data['Im'],
        )
        if f_eval_kk is not None:
            _add_series_to_plot({'f': f_eval_kk, 'y': residual_re_kk}, y_axis_re, "KKsmooth_ReIm_Re", False)
            _add_series_to_plot({'f': f_eval_kk, 'y': residual_im_kk}, y_axis_re, "KKsmooth_ReIm_Im", False)
    dpg.add_plot_legend(parent=f"{parent_tag}_ReIm_residual")

    y_axis_im = _create_plot_with_axes(
        f"{parent_tag}_Re_residual", -1, -1,
        "Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]", "Residual [%]", log_x=True
    )
    f_eval, residual_re, residual_im = _compute_residual_series(
        ref_data['f'],
        ref_data['Re'],
        ref_data['Im'],
        ref_data['Z'],
        drt_data['Re']['f'],
        drt_data['Re']['Re'],
        drt_data['Re']['Im'],
    )
    if f_eval is None:
        print("-- Warning: Failed to build Re residual series due to invalid overlap.")
    else:
        _add_series_to_plot({'f': f_eval, 'y': residual_re}, y_axis_im, "DRT_Re_Re", False)
        _add_series_to_plot({'f': f_eval, 'y': residual_im}, y_axis_im, "DRT_Re_Im", False)
    if isinstance(extra_drt_data, dict) and extra_drt_data.get('Re', None) is not None:
        f_eval_extra, residual_re_extra, residual_im_extra = _compute_residual_series(
            ref_data['f'],
            ref_data['Re'],
            ref_data['Im'],
            ref_data['Z'],
            extra_drt_data['Re']['f'],
            extra_drt_data['Re']['Re'],
            extra_drt_data['Re']['Im'],
        )
        if f_eval_extra is not None:
            _add_series_to_plot({'f': f_eval_extra, 'y': residual_re_extra}, y_axis_im, f"{extra_label}_Re_Re", False)
            _add_series_to_plot({'f': f_eval_extra, 'y': residual_im_extra}, y_axis_im, f"{extra_label}_Re_Im", False)
    if isinstance(kk_smooth_data, dict) and kk_smooth_data.get('f', None) is not None:
        f_eval_kk, residual_re_kk, residual_im_kk = _compute_residual_series(
            ref_data['f'],
            ref_data['Re'],
            ref_data['Im'],
            ref_data['Z'],
            kk_smooth_data['f'],
            kk_smooth_data['Re'],
            kk_smooth_data['Im'],
        )
        if f_eval_kk is not None:
            _add_series_to_plot({'f': f_eval_kk, 'y': residual_re_kk}, y_axis_im, "KKsmooth_Re_Re", False)
            _add_series_to_plot({'f': f_eval_kk, 'y': residual_im_kk}, y_axis_im, "KKsmooth_Re_Im", False)
    dpg.add_plot_legend(parent=f"{parent_tag}_Re_residual")

def _update_eis_truncated_views(data, parent_tag, data_category):
    extra_series = None
    zhit_smooth = _get_zhit_smooth_eis(data)
    if zhit_smooth is not None:
        extra_series = {
            'label': 'ZHIT',
            'smooth': zhit_smooth,
            # Keep only ZHIT smooth overlay here. DRT curve must come from truncated DRT only.
            'drt': None,
        }

    _plot_three_views_with_drt(
        data,
        parent_tag,
        data_category,
        measured=data.truncated,
        measured_label="truncated",
        smooth=data.smooth,
        smooth_label="KK_smooth",
        drt_data=data.tknv_truncated,
        extra_series=extra_series,
    )


def _render_single_gamma_distribution(parent_tag, data, data_type):
    if data[f"tknv_{data_type}"] is None:
        dpg.add_text(f"No DRT data for {data_type}.", parent=parent_tag)
        return

    with dpg.plot(
        tag=f"{parent_tag}_{data_type}_gamma_single",
        width=-1,
        height=-1,
        no_menus=False,
        parent=parent_tag,
    ):
        dpg.add_plot_axis(
            dpg.mvXAxis,
            label="Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]",
            log_scale=True,
        )
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")

        y_max_value = 0.0
        y_min_value = 0.0
        has_series = False
        for category in ["ReIm", "Re", "Im"]:
            if category not in data[f"tknv_{data_type}"]:
                continue
            g_arr = data[f"tknv_{data_type}"][category]['g']
            if g_arr is None or len(g_arr) == 0:
                continue
            has_series = True
            y_max_value = max(y_max_value, float(np.max(g_arr)))
            y_min_value = min(y_min_value, float(np.min(g_arr)))
            _add_series_to_plot(
                {'f': data[f"tknv_{data_type}"][category]['f'], 'y': g_arr},
                y_axis,
                category,
            )

        if has_series:
            y_upper = y_max_value * 1.1 if y_max_value > 0 else 1.0
            if y_upper == y_min_value:
                y_upper = y_min_value + 1.0
            dpg.set_axis_limits(y_axis, y_min_value, y_upper)
            dpg.add_plot_legend()


def _render_single_kk_residual(parent_tag, data, has_zhit_tknv):
    subtab_tag = f"{parent_tag}_subtab"
    if not _ensure_or_reset_tab_bar(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(f"{parent_tag}_tab_reim", "ReIm", subtab_tag)
    _ensure_or_clear_tab(f"{parent_tag}_tab_re", "Re", subtab_tag)
    _ensure_or_clear_tab(f"{parent_tag}_tab_im", "Im", subtab_tag)
    _ensure_or_clear_tab(f"{parent_tag}_tab_residual", "Residuals", subtab_tag)

    # Cleanup legacy tabs kept from previous UI versions.
    if dpg.does_item_exist(f"{parent_tag}_tab_zhit"):
        dpg.delete_item(f"{parent_tag}_tab_zhit")
    if dpg.does_item_exist(f"{parent_tag}_tab_zhit_residual"):
        dpg.delete_item(f"{parent_tag}_tab_zhit_residual")

    with dpg.group(parent=f"{parent_tag}_tab_reim"):
        _update_eis_truncated_views(data, f"{parent_tag}_reim", "ReIm")
    with dpg.group(parent=f"{parent_tag}_tab_re"):
        _update_eis_truncated_views(data, f"{parent_tag}_re", "Re")
    with dpg.group(parent=f"{parent_tag}_tab_im"):
        _update_eis_truncated_views(data, f"{parent_tag}_im", "Im")
    with dpg.group(parent=f"{parent_tag}_tab_residual"):
        _plot_residuals(
            f"{parent_tag}_residual",
            data.truncated,
            data.tknv_truncated,
            extra_drt_data=data.tknv_zhit if has_zhit_tknv else None,
            extra_label="ZHIT",
            kk_smooth_data=data.smooth,
        )


def _render_all_gamma_distribution(parent_tag, config, data_type):
    subtab_tag = f"{parent_tag}_{data_type}_subtab"
    if not _ensure_or_reset_tab_bar(subtab_tag, parent_tag):
        return

    _ensure_or_clear_tab(f"{parent_tag}_{data_type}_reim", "ReIm", subtab_tag)
    _ensure_or_clear_tab(f"{parent_tag}_{data_type}_re", "Re", subtab_tag)
    _ensure_or_clear_tab(f"{parent_tag}_{data_type}_im", "Im", subtab_tag)

    for category, tab_id in [
        ("ReIm", f"{parent_tag}_{data_type}_reim"),
        ("Re", f"{parent_tag}_{data_type}_re"),
        ("Im", f"{parent_tag}_{data_type}_im"),
    ]:
        with dpg.group(parent=tab_id):
            with dpg.plot(
                tag=f"{tab_id}_plot",
                width=-1,
                height=-1,
                no_menus=False,
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    label="Frequency [Hz]" if not dpg.get_value('check_box_drt_tau') else "Tau [s]",
                    log_scale=True,
                )
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="gamma [ohm·s·cm2]")

                y_max_value = 0.0
                y_min_value = 0.0
                has_series = False
                for file_name in config.selected_files:
                    file_key = os.path.splitext(file_name)[0]
                    if file_key not in config.store or 'EIS' not in config.store[file_key]:
                        continue
                    data = config.store[file_key]['EIS']
                    tknv_data = data[f"tknv_{data_type}"]
                    if tknv_data is None or category not in tknv_data:
                        continue
                    g_arr = tknv_data[category]['g']
                    if g_arr is None or len(g_arr) == 0:
                        continue
                    has_series = True
                    _add_series_to_plot(
                        {'f': tknv_data[category]['f'], 'y': g_arr},
                        y_axis,
                        label=gui_utils.small_functions.string_abbreviation(file_key, 12, 12),
                        is_line=True,
                    )
                    y_max_value = max(y_max_value, float(np.max(g_arr)))
                    y_min_value = min(y_min_value, float(np.min(g_arr)))

                if has_series:
                    y_upper = y_max_value * 1.1 if y_max_value > 0 else 1.0
                    if y_upper == y_min_value:
                        y_upper = y_min_value + 1.0
                    dpg.set_axis_limits(y_axis, y_min_value, y_upper)
                    dpg.add_plot_legend(parent=f"{tab_id}_plot", location=dpg.mvPlot_Location_NorthEast)


def _sanitize_lambda_curve(curve):
    if not isinstance(curve, dict):
        return None

    lambda_values = np.asarray(curve.get('lambda_values', []), dtype=float).reshape(-1)
    norm_res = np.asarray(curve.get('norm_res', []), dtype=float).reshape(-1)
    norm_drt = np.asarray(curve.get('norm_drt', []), dtype=float).reshape(-1)
    curvature = np.asarray(curve.get('curvature', []), dtype=float).reshape(-1)

    n = min(len(lambda_values), len(norm_res), len(norm_drt), len(curvature))
    if n < 2:
        return None

    lambda_values = lambda_values[:n]
    norm_res = norm_res[:n]
    norm_drt = norm_drt[:n]
    curvature = curvature[:n]

    # L-curve plot uses log-log axes, so x/y must be strictly positive and finite.
    valid_l = (
        np.isfinite(lambda_values)
        & np.isfinite(norm_res)
        & np.isfinite(norm_drt)
        & (lambda_values > 0)
        & (norm_res > 0)
        & (norm_drt > 0)
    )

    # Curvature plot uses log x-axis only.
    valid_c = np.isfinite(lambda_values) & np.isfinite(curvature) & (lambda_values > 0)

    if np.count_nonzero(valid_l) < 2 or np.count_nonzero(valid_c) < 2:
        return None

    lam_l = lambda_values[valid_l]
    res_l = norm_res[valid_l]
    drt_l = norm_drt[valid_l]

    lam_c = lambda_values[valid_c]
    cur_c = curvature[valid_c]

    lambda_opt = float(curve.get('lambda_optimal', np.nan))
    if not np.isfinite(lambda_opt) or lambda_opt <= 0:
        # Fallback to max curvature point on valid curvature series.
        lambda_opt = float(lam_c[int(np.argmax(cur_c))])

    idx_l = int(np.argmin(np.abs(np.log10(lam_l) - np.log10(lambda_opt))))
    idx_c = int(np.argmin(np.abs(np.log10(lam_c) - np.log10(lambda_opt))))

    return {
        'lambda_opt': lambda_opt,
        'lam_l': lam_l,
        'res_l': res_l,
        'drt_l': drt_l,
        'idx_l': idx_l,
        'lam_c': lam_c,
        'cur_c': cur_c,
        'idx_c': idx_c,
    }


def _has_lambda_curve(data):
    if not hasattr(data, 'store') or not isinstance(data.store, dict):
        return False
    return _sanitize_lambda_curve(data.store.get('LambdaOPT_curve', None)) is not None


def _render_lambda_curve_single(parent_tag, data):
    if not dpg.does_item_exist(parent_tag):
        print(f"-- Warning: L-curve single parent '{parent_tag}' not found.")
        return

    curve = data.store.get('LambdaOPT_curve', None) if hasattr(data, 'store') else None
    curve_plot = _sanitize_lambda_curve(curve)
    if curve_plot is None:
        dpg.add_text("No L-curve data. Click 'Compute lambda' first.", parent=parent_tag)
        return

    with dpg.plot(tag=f"{parent_tag}_lcurve", width=-1, height=int(dpg.get_viewport_height() * 0.42), no_menus=False, parent=parent_tag):
        dpg.add_plot_axis(dpg.mvXAxis, label="||A*gamma-b||", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="||gamma||", log_scale=True)
        dpg.add_line_series(curve_plot['res_l'], curve_plot['drt_l'], parent=y_axis, label="L-curve")
        dpg.add_scatter_series(
            [curve_plot['res_l'][curve_plot['idx_l']]],
            [curve_plot['drt_l'][curve_plot['idx_l']]],
            parent=y_axis,
            label=f"opt lambda={curve_plot['lambda_opt']:.3e}",
        )
        dpg.add_plot_legend(parent=f"{parent_tag}_lcurve")

    with dpg.plot(tag=f"{parent_tag}_curvature", width=-1, height=-1, no_menus=False, parent=parent_tag):
        dpg.add_plot_axis(dpg.mvXAxis, label="lambda", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Curvature")
        dpg.add_line_series(curve_plot['lam_c'], curve_plot['cur_c'], parent=y_axis, label="k(lambda)")
        dpg.add_scatter_series(
            [curve_plot['lam_c'][curve_plot['idx_c']]],
            [curve_plot['cur_c'][curve_plot['idx_c']]],
            parent=y_axis,
            label="selected",
        )
        dpg.add_plot_legend(parent=f"{parent_tag}_curvature")


def _render_lambda_curve_all(parent_tag, config):
    if not dpg.does_item_exist(parent_tag):
        print(f"-- Warning: L-curve all parent '{parent_tag}' not found.")
        return

    with dpg.plot(tag=f"{parent_tag}_lcurve", width=-1, height=int(dpg.get_viewport_height() * 0.42), no_menus=False, parent=parent_tag):
        dpg.add_plot_axis(dpg.mvXAxis, label="||A*gamma-b||", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="||gamma||", log_scale=True)
        has_series = False
        for file_name in config.selected_files:
            file_key = os.path.splitext(file_name)[0]
            if file_key not in config.store or 'EIS' not in config.store[file_key]:
                continue
            eis_data = config.store[file_key]['EIS']
            curve = eis_data.store.get('LambdaOPT_curve', None) if hasattr(eis_data, 'store') else None
            curve_plot = _sanitize_lambda_curve(curve)
            if curve_plot is None:
                continue
            label = gui_utils.small_functions.string_abbreviation(file_key, 12, 12)
            dpg.add_line_series(curve_plot['res_l'], curve_plot['drt_l'], parent=y_axis, label=f"L:{label}")
            dpg.add_scatter_series(
                [curve_plot['res_l'][curve_plot['idx_l']]],
                [curve_plot['drt_l'][curve_plot['idx_l']]],
                parent=y_axis,
                label=f"opt:{label}",
            )
            has_series = True

        if has_series:
            dpg.add_plot_legend(parent=f"{parent_tag}_lcurve", location=dpg.mvPlot_Location_NorthEast)

    with dpg.plot(tag=f"{parent_tag}_curvature", width=-1, height=-1, no_menus=False, parent=parent_tag):
        dpg.add_plot_axis(dpg.mvXAxis, label="lambda", log_scale=True)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Curvature")
        has_series = False
        for file_name in config.selected_files:
            file_key = os.path.splitext(file_name)[0]
            if file_key not in config.store or 'EIS' not in config.store[file_key]:
                continue
            eis_data = config.store[file_key]['EIS']
            curve = eis_data.store.get('LambdaOPT_curve', None) if hasattr(eis_data, 'store') else None
            curve_plot = _sanitize_lambda_curve(curve)
            if curve_plot is None:
                continue
            label = gui_utils.small_functions.string_abbreviation(file_key, 12, 12)
            dpg.add_line_series(curve_plot['lam_c'], curve_plot['cur_c'], parent=y_axis, label=f"k:{label}")
            dpg.add_scatter_series(
                [curve_plot['lam_c'][curve_plot['idx_c']]],
                [curve_plot['cur_c'][curve_plot['idx_c']]],
                parent=y_axis,
                label=f"sel:{label}",
            )
            has_series = True

        if has_series:
            dpg.add_plot_legend(parent=f"{parent_tag}_curvature", location=dpg.mvPlot_Location_NorthEast)

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

    if not dpg.does_item_exist("tab_bar_drt_plot_single"):
        print("---- Skipped: tab_bar_drt_plot_single not found.")
        return

    file_key = os.path.splitext(config.display_file)[0]
    data = config.store[file_key]['EIS']
    has_zhit_tknv = _has_zhit_tknv(data)
    has_lcurve = _has_lambda_curve(data)

    for stale_tab in [
        "tab_drt_smooth_plot_single",
        "tab_drt_LCcorrect_plot_single",
        "tab_drt_extrapolation_plot_single",
    ]:
        if dpg.does_item_exist(stale_tab):
            dpg.delete_item(stale_tab)

    # Keep top-level tabs alive (like EIS) and only refresh their children.
    _ensure_or_clear_tab("tab_drt_truncated_plot_single", "Truncated", "tab_bar_drt_plot_single")
    _ensure_tab_exists("tab_drt_kk_plot_single", "KK", "tab_bar_drt_plot_single")

    if has_zhit_tknv:
        _ensure_or_clear_tab("tab_drt_zhit_plot_single", "ZHIT", "tab_bar_drt_plot_single")

    if has_lcurve:
        _ensure_or_clear_tab("tab_drt_lcurve_plot_single", "L-curve", "tab_bar_drt_plot_single")

    _ensure_tab_exists("tab_drt_EIS_truncated_plot_single", "EIS_truncated", "tab_bar_drt_plot_single")

    _render_single_gamma_distribution("tab_drt_truncated_plot_single", data, "truncated")
    if has_lcurve:
        _render_lambda_curve_single("tab_drt_lcurve_plot_single", data)
    _render_single_kk_residual("tab_drt_EIS_truncated_plot_single", data, has_zhit_tknv)

    if not _ensure_or_reset_tab_bar("tab_bar_drt_kk_plot_single", "tab_drt_kk_plot_single"):
        print("---- Skipped: KK single tab bar could not be created.")
        return

    _ensure_or_clear_tab("tab_drt_kk_smooth_plot_single", "Smooth", "tab_bar_drt_kk_plot_single")
    _ensure_or_clear_tab("tab_drt_kk_lccorrect_plot_single", "LCcorrect", "tab_bar_drt_kk_plot_single")
    _ensure_or_clear_tab("tab_drt_kk_extrapolation_plot_single", "Extrapolation", "tab_bar_drt_kk_plot_single")

    _render_single_gamma_distribution("tab_drt_kk_smooth_plot_single", data, "smooth")
    _render_single_gamma_distribution("tab_drt_kk_lccorrect_plot_single", data, "LCcorrect")
    _render_single_gamma_distribution("tab_drt_kk_extrapolation_plot_single", data, "extrapolation")

    if has_zhit_tknv:
        _render_single_gamma_distribution("tab_drt_zhit_plot_single", data, "zhit")

    print("---- DRT single plots updated successfully.")

def update_all_plots(config):
    """Update multi-file DRT comparison plots (gamma distribution only)."""
    print("-- Updating DRT gamma distribution plots...")
    
    if not config.selected_files:
        print("---- Skipped: No files selected.")
        return

    if not dpg.does_item_exist("tab_bar_drt_plot_all"):
        print("---- Skipped: tab_bar_drt_plot_all not found.")
        return

    has_any_zhit_tknv = False
    has_any_lcurve = False
    for file_name in config.selected_files:
        file_key = os.path.splitext(file_name)[0]
        if file_key in config.store and 'EIS' in config.store[file_key]:
            eis_data = config.store[file_key]['EIS']
            if _has_zhit_tknv(eis_data):
                has_any_zhit_tknv = True
            if _has_lambda_curve(eis_data):
                has_any_lcurve = True

    for stale_tab in [
        "tab_drt_smooth_plot_all",
        "tab_drt_LCcorrect_plot_all",
        "tab_drt_extrapolation_plot_all",
    ]:
        if dpg.does_item_exist(stale_tab):
            dpg.delete_item(stale_tab)

    _ensure_or_clear_tab("tab_drt_truncated_plot_all", "Truncated", "tab_bar_drt_plot_all")
    _ensure_or_clear_tab("tab_drt_kk_plot_all", "KK", "tab_bar_drt_plot_all")
    if has_any_lcurve:
        _ensure_or_clear_tab("tab_drt_lcurve_plot_all", "L-curve", "tab_bar_drt_plot_all")
    elif dpg.does_item_exist("tab_drt_lcurve_plot_all"):
        dpg.delete_item("tab_drt_lcurve_plot_all")

    if has_any_zhit_tknv:
        _ensure_or_clear_tab("tab_drt_zhit_plot_all", "ZHIT", "tab_bar_drt_plot_all")
    elif dpg.does_item_exist("tab_drt_zhit_plot_all"):
        dpg.delete_item("tab_drt_zhit_plot_all")

    _render_all_gamma_distribution("tab_drt_truncated_plot_all", config, "truncated")
    if has_any_lcurve:
        _render_lambda_curve_all("tab_drt_lcurve_plot_all", config)

    if not _ensure_or_reset_tab_bar("tab_bar_drt_kk_plot_all", "tab_drt_kk_plot_all"):
        print("---- Skipped: KK all tab bar could not be created.")
        return

    _ensure_or_clear_tab("tab_drt_kk_smooth_plot_all", "Smooth", "tab_bar_drt_kk_plot_all")
    _ensure_or_clear_tab("tab_drt_kk_lccorrect_plot_all", "LCcorrect", "tab_bar_drt_kk_plot_all")
    _ensure_or_clear_tab("tab_drt_kk_extrapolation_plot_all", "Extrapolation", "tab_bar_drt_kk_plot_all")

    _render_all_gamma_distribution("tab_drt_kk_smooth_plot_all", config, "smooth")
    _render_all_gamma_distribution("tab_drt_kk_lccorrect_plot_all", config, "LCcorrect")
    _render_all_gamma_distribution("tab_drt_kk_extrapolation_plot_all", config, "extrapolation")

    if has_any_zhit_tknv:
        _render_all_gamma_distribution("tab_drt_zhit_plot_all", config, "zhit")

    print("---- DRT gamma distribution plots updated successfully.")
