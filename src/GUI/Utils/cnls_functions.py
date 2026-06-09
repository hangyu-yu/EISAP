import os
import copy
import math
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
import src.Methods.CNLS.Utils as CNLS_fn
from src.Methods.CNLS.Circuit import Circuit


CNLS_SELECTOR_WINDOW_TAG = "window_cnls_selector"
CNLS_SELECTOR_DRAWLIST_TAG = "cnls_selector_preview_drawlist"
CNLS_SELECTOR_REMOVE_LIST_TAG = "cnls_selector_remove_list"
CNLS_SELECTOR_ADD_TABLE_TAG = "cnls_selector_add_table"
CNLS_SELECTOR_REMOVE_STATUS_TAG = "cnls_selector_remove_status"
CNLS_SELECTOR_EDIT_KEY = "_selector_elements_buffer"


_selector_remove_selected_names = []


_SELECTOR_PARAM_LIST = {
    'Inductor': ([1], [np.inf], [1e-10]),
    'Resistor': ([1], [np.inf], [1e-10]),
    'Capacitor': ([1], [np.inf], [1e-10]),
    'CPE': ([1, 1], [np.inf, 1], [1e-10, 0.4]),
    'Inductor_a': ([1, 1], [np.inf, 1], [1e-10, 0.4]),
    'RC': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
    'RQ': ([1, 1, 1], [np.inf, np.inf, 1], [1e-10, 1e-10, 0.4]),
    'Gerisher': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
    'fFLW': ([1, 1, 1], [np.inf, np.inf, 1], [1e-10, 1e-10, 0.4]),
    'FLW': ([1, 1], [np.inf, np.inf], [1e-10, 1e-10]),
    'Warburg': ([1], [np.inf], [1e-10]),
    'RandleC': ([1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf], [1e-10, 1e-10, 1e-10, 1e-10]),
    'RandleCfFLW': ([1, 1, 1, 1, 1], [np.inf, np.inf, np.inf, np.inf, 1], [1e-10, 1e-10, 1e-10, 1e-10, 0.4]),
    'RandleCPE': ([1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf], [1e-10, 1e-10, 0.4, 1e-10, 1e-10]),
    'RandleCPEfFLW': ([1, 1, 1, 1, 1, 1], [np.inf, np.inf, 1, np.inf, np.inf, 1], [1e-10, 1e-10, 0.4, 1e-10, 1e-10, 0.4]),
}


def _default_cnls_elements():
    return [
        {'name': 'L1', 'type': 'Inductor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
        {'name': 'R2', 'type': 'Resistor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
    ]


def _ensure_store_elements(config):
    elements = config.store.get("Elements", None)
    if not isinstance(elements, list) or len(elements) == 0:
        config.store["Elements"] = copy.deepcopy(_default_cnls_elements())
    return config.store["Elements"]

def _file_existence_check(config):
    """Check if the file exists in the store and contains valid CNLS data.
    
    Args:
        config: Configuration object containing store and display_file.
        
    Returns:
        bool: Whether the file exists and the data is valid.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    return (file_name_no_ext in config.store and 
            config.store[file_name_no_ext] is not None and 
            config.store[file_name_no_ext].get('CNLS') is not None and 
            config.store[file_name_no_ext]['CNLS'].f_fixed is not None)


def normalize_cnls_data_type(data_type):
    """Public normalizer used by GUI refresh code and CNLS callbacks."""
    return CNLS_fn.normalize_cnls_data_type(data_type)[0]


def _resolve_cnls_reference_data(eis_data, data_type):
    return CNLS_fn.resolve_cnls_reference(eis_data, data_type, allow_rbf_fallback=True)


def apply_cnls_reference_data(cnls_data, eis_data):
    """Fill CNLS reference vectors (DRTmes/Zmes/f/w) from the selected data_type."""
    reference = _resolve_cnls_reference_data(eis_data, cnls_data.data_type)
    if reference is None:
        reference = _resolve_cnls_reference_data(eis_data, "truncated")
        if reference is None:
            raise ValueError("CNLS reference data missing: no valid DRT reference (Tikhonov/RBF).")
        print("[Warning] CNLS reference fallback to truncated (Tikhonov): selected data unavailable.")

    if reference["normalized_data_type"] != cnls_data.data_type:
        print(
            f"[Warning] CNLS data type '{cnls_data.data_type}' fallback to '{reference['normalized_data_type']}' "
            f"for current file."
        )
        cnls_data.data_type = reference["normalized_data_type"]

    cnls_data.DRTmes = reference["drt_mes"]
    cnls_data.f = reference["z_f"]
    cnls_data.f_drt = reference.get("drt_f", reference["z_f"])
    cnls_data.Zmes = reference["z_mes"]
    cnls_data.w = cnls_data.f * 2 * np.pi if cnls_data.f is not None else None

    if len(cnls_data.Zmes) != len(cnls_data.f):
        raise ValueError(
            f"CNLS fitting axis mismatch: len(Zmes)={len(cnls_data.Zmes)} vs len(f)={len(cnls_data.f)}"
        )

    return reference

def _update_peak_fixed(sender, app_data, config):
    print("-- Updating peak fixed frequency...")
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    if app_data == 0:
        config.store["peak_fixed_frequencies"] = []
        for j in range(dpg.get_value("input_nbr_peaks")):
            if _file_existence_check(config) and j <= len(config.store[file_name_no_ext]['CNLS'].f_fixed)-1:
                # Always store frequency, never tau conversion here
                config.store["peak_fixed_frequencies"].append(config.store[file_name_no_ext]['CNLS'].f_fixed[j])
            else:
                config.store["peak_fixed_frequencies"].append(10**(dpg.get_value("input_nbr_peaks")-j-2))
        print("---- Peak fixed frequencies updated.")
    else:
        # Convert user input to frequency if x_tau is enabled
        if dpg.get_value("check_box_cnls_tau"):
            # User entered tau, convert back to frequency for storage
            freq_value = 1 / (2 * np.pi * app_data) if app_data != 0 else app_data
        else:
            # User entered frequency directly
            freq_value = app_data
        config.store["peak_fixed_frequencies"][int(sender[-1])] = freq_value
        print(f"---- Peak fixed frequency {int(sender[-1])+1} updated.")

    try:
        config.store[file_name_no_ext]['CNLS'].f_fixed = config.store["peak_fixed_frequencies"]
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")
    
def _peak_value_set(config, nbr_peaks, i):
    """Set the default peak frequency values with exponential spacing.
    
    Args:
        config: Configuration object.
        nbr_peaks: Number of peaks to set.
        i: Index of the peak.
        
    Returns:
        float: Display value (frequency or tau depending on check_box_cnls_tau state).
    """
    # Always get stored frequency value
    freq_value = config.store["peak_fixed_frequencies"][i] if i <= len(config.store["peak_fixed_frequencies"])-1 else 10**(nbr_peaks-i-2)
    
    # Convert to tau for display if x_tau is enabled
    if dpg.get_value("check_box_cnls_tau"):
        return_value = 1 / (2 * np.pi * freq_value) if freq_value != 0 else freq_value
    else:
        return_value = freq_value
    return return_value
    
def constraint_percentage(CNLS_tmp):
    """Set the constraint percentage for R and Tau.
    
    Args:
        CNLS_tmp: CNLS object.
        config: Configuration object.
    """
    if dpg.get_value("checkbox_cnls_R_percentage"):
        RIndex = [i for i, name in enumerate(CNLS_tmp.ElementsParamNames) if '_R' in name]
        R_percentage = dpg.get_value("input_constraints_R_percentage")
        R = np.array(CNLS_tmp.ElementsParamValues)[RIndex]
        CNLS_tmp.UpperBound[RIndex] = R*(1+R_percentage/100)
        CNLS_tmp.LowerBound[RIndex] = R*(1-R_percentage/100)
        print("---- R constraint set to percentage mode.")
    else:
        RIndex = [i for i, name in enumerate(CNLS_tmp.ElementsParamNames) if '_R' in name]
        R = np.array(CNLS_tmp.ElementsParamValues)[RIndex]
        CNLS_tmp.UpperBound[RIndex] = np.inf
        CNLS_tmp.LowerBound[RIndex] = 1e-10
    
    if dpg.get_value("checkbox_cnls_Tau_percentage"):
        TauIndex = [i for i, name in enumerate(CNLS_tmp.ElementsParamNames) if 'tau' in name]
        Tau_percentage = dpg.get_value("input_constraints_Tau_percentage")
        tau = np.array(CNLS_tmp.ElementsParamValues)[TauIndex]
        tau_bound1 = np.exp(np.log(tau) * (1 - Tau_percentage / 100))
        tau_bound2 = np.exp(np.log(tau) * (1 + Tau_percentage / 100))
        CNLS_tmp.UpperBound[TauIndex] = np.maximum(tau_bound1, tau_bound2)
        CNLS_tmp.LowerBound[TauIndex] = np.minimum(tau_bound1, tau_bound2)

        print("---- Tau constraint set to percentage mode.")

    for idx, element in enumerate(CNLS_tmp.Elements):
        start_idx = CNLS_tmp.ElementsStartIndex[idx]
        end_idx = CNLS_tmp.ElementsEndIndex[idx] + 1
        CNLS_tmp.Elements[idx]['Param'] = CNLS_tmp.ElementsParamValues[start_idx:end_idx]
        CNLS_tmp.Elements[idx]['Ub'] = CNLS_tmp.UpperBound[start_idx:end_idx].tolist()
        CNLS_tmp.Elements[idx]['Lb'] = CNLS_tmp.LowerBound[start_idx:end_idx].tolist()

def dynamic_peak_ids(sender, appdata, config):
    """Dynamically generate peak frequency input columns.
    
    Args:
        config: Configuration object.
    """
    nbr_peaks = dpg.get_value("input_nbr_peaks")
    enable_state = True
    _update_peak_fixed(None, 0, config)
    if 'nbr_peaks' in config.store.keys():
        for i in range(config.store['nbr_peaks']):
            if dpg.does_item_exist(f"table_row_peak_{i}"):
                dpg.delete_item(f"table_row_peak_{i}")

    # Generate table rows
    for i in range(nbr_peaks):
        # Set column headers
        if i == 0:
            label = "High f [Hz]" if not dpg.get_value("check_box_cnls_tau") else "Low tau [s]"
        elif i == nbr_peaks-1:
            label = "Low f [Hz]" if not dpg.get_value("check_box_cnls_tau") else "High tau [s]"
        else:
            label = ""
        
        # Set default values (default values with exponential spacing)
        
        with dpg.table_row(parent="Table_cnls_parameters", tag=f"table_row_peak_{i}"):
            dpg.add_text(tag=f"cnls_text_peak_{i}", default_value=label)
            dpg.add_input_float(
                tag=f"input_peak_{i}",
                format="%.3f" if not dpg.get_value("check_box_cnls_tau") else "%.3e",
                enabled=enable_state,
                default_value= _peak_value_set(config, nbr_peaks, i),
                width=-1,
                step=0,
                step_fast=0,
                min_value=1e-100,
                max_value=1e100,
                callback=lambda s, a: _update_peak_fixed(s, a, config)
            )
    config.store['nbr_peaks'] = nbr_peaks


PEAK_SELECT_WINDOW_TAG = "cnls_peak_select_window"
PEAK_SELECT_HANDLERS_TAG = "cnls_peak_select_handlers"

# Indices (into the DRT point array) currently selected in the open selector window.
_peak_select_indices = set()


def _close_peak_select_window():
    if dpg.does_item_exist(PEAK_SELECT_HANDLERS_TAG):
        dpg.delete_item(PEAK_SELECT_HANDLERS_TAG)
    if dpg.does_item_exist(PEAK_SELECT_WINDOW_TAG):
        dpg.delete_item(PEAK_SELECT_WINDOW_TAG)


def open_peak_select_window(config):
    """Open a window showing the DRT data points so the user can pick peak positions.

    Points are selected by clicking them on the scatter plot; the left panel lists
    only the currently selected points. The x-axis follows the 'x-tau' option
    (frequency or tau). On apply, selected points are ranked from high to low
    frequency and written into the peak frequency list, with 'Nbr peaks' updated
    to the number of selected points.
    """
    import src.GUI.Utils.progress_modal as _pm

    if config.display_file in (None, "", []):
        return

    file_key = os.path.splitext(config.display_file)[0]
    if (file_key not in config.store or 'CNLS' not in config.store[file_key]
            or config.store[file_key].get('EIS') is None):
        _pm.show_error_dialog(
            "CNLS — Select Peaks",
            f"'{config.display_file}' has no processed CNLS/EIS data.\n"
            "Please initialize the data before selecting peaks."
        )
        return

    CNLS_tmp = config.store[file_key]['CNLS']
    EIS_tmp = config.store[file_key]['EIS']
    try:
        apply_cnls_reference_data(CNLS_tmp, EIS_tmp)
    except Exception as e:
        _pm.show_error_dialog("CNLS — Select Peaks", f"DRT reference data unavailable:\n{e}")
        return

    f_drt = CNLS_tmp.f_drt if getattr(CNLS_tmp, "f_drt", None) is not None else CNLS_tmp.f
    drt = CNLS_tmp.DRTmes
    if f_drt is None or drt is None or len(f_drt) == 0:
        _pm.show_error_dialog("CNLS — Select Peaks", "No DRT data points available for this file.")
        return

    f_drt = np.asarray(f_drt, dtype=float)
    drt = np.asarray(drt, dtype=float)
    n = len(f_drt)

    use_tau = dpg.get_value("check_box_cnls_tau")
    x_vals = f_drt if not use_tau else 1.0 / (2.0 * np.pi * f_drt)
    x_label = "Frequency [Hz]" if not use_tau else "tau [s]"

    # Pre-select grid points nearest to the stored fixed frequencies, but only when
    # an existing CNLS data file is present. For a fresh file (no saved CNLS .xlsx),
    # start with a cleared selection instead of mapping the default frequencies.
    _peak_select_indices.clear()
    _folder = getattr(CNLS_tmp, "file_folder", None) or config.folder_path
    _fname = getattr(CNLS_tmp, "filename", None) or config.display_file
    has_existing_cnls = False
    try:
        if _folder and _fname:
            _cnls_file = os.path.join(_folder, "CNLS", os.path.splitext(os.path.basename(_fname))[0] + ".xlsx")
            has_existing_cnls = os.path.exists(_cnls_file)
    except Exception:
        has_existing_cnls = False

    # Pre-select when a saved CNLS file exists OR the user already applied a
    # selection for this file in this session; otherwise start cleared.
    applied = config.store.get("cnls_peaks_applied", set())
    if has_existing_cnls or file_key in applied:
        f_fixed = getattr(CNLS_tmp, "f_fixed", None)
        if f_fixed is not None:
            for ff in f_fixed:
                try:
                    _peak_select_indices.add(int(np.argmin(np.abs(f_drt - float(ff)))))
                except Exception:
                    continue

    # Precompute log-x for robust nearest-point detection on a log axis.
    with np.errstate(divide='ignore', invalid='ignore'):
        log_x = np.log10(np.where(x_vals > 0, x_vals, np.nan))
    x_range = (np.nanmax(log_x) - np.nanmin(log_x)) or 1.0
    y_range = (np.nanmax(drt) - np.nanmin(drt)) or 1.0

    def _update_sel_series():
        sel = sorted(_peak_select_indices)
        sx = [float(x_vals[i]) for i in sel]
        sy = [float(drt[i]) for i in sel]
        if dpg.does_item_exist("cnls_peak_select_series_sel"):
            dpg.set_value("cnls_peak_select_series_sel", [sx, sy])
        if dpg.does_item_exist("cnls_peak_select_count"):
            dpg.set_value("cnls_peak_select_count", f"Selected peaks: {len(sel)}")

    def _refresh_selected_table():
        if not dpg.does_item_exist("cnls_peak_select_table"):
            return
        dpg.delete_item("cnls_peak_select_table", children_only=True, slot=1)
        # Rank selected points high -> low frequency.
        for rank, i in enumerate(sorted(_peak_select_indices, key=lambda k: f_drt[k], reverse=True)):
            with dpg.table_row(parent="cnls_peak_select_table"):
                dpg.add_text(str(rank + 1))
                dpg.add_text(f"{float(f_drt[i]):.4e}")
                dpg.add_text(f"{1.0 / (2.0 * np.pi * float(f_drt[i])):.4e}")
                dpg.add_text(f"{float(drt[i]):.4e}")
                dpg.add_button(label="x", small=True, user_data=i, callback=_remove_index)

    def _remove_index(sender, app_data, user_data):
        _peak_select_indices.discard(int(user_data))
        _update_sel_series()
        _refresh_selected_table()

    def _nearest_idx(mx, my):
        lmx = np.log10(mx) if mx > 0 else np.nanmin(log_x)
        dist = ((log_x - lmx) / x_range) ** 2 + ((drt - my) / y_range) ** 2
        return int(np.nanargmin(dist))

    def _hover():
        if not dpg.is_item_hovered("cnls_peak_select_plot"):
            return
        mx, my = dpg.get_plot_mouse_pos()
        idx = _nearest_idx(mx, my)
        # Pointer marker follows the nearest data point under the cursor.
        if dpg.does_item_exist("cnls_peak_select_series_ptr"):
            dpg.set_value("cnls_peak_select_series_ptr", [[float(x_vals[idx])], [float(drt[idx])]])
        dpg.set_value(
            "cnls_peak_select_hover",
            f"Pointer -> Index: {idx + 1} | f: {f_drt[idx]:.3e} Hz | "
            f"tau: {1.0 / (2.0 * np.pi * f_drt[idx]):.3e} s | gamma: {drt[idx]:.3e}"
        )

    def _toggle_nearest():
        if not dpg.is_item_hovered("cnls_peak_select_plot"):
            return
        mx, my = dpg.get_plot_mouse_pos()
        idx = _nearest_idx(mx, my)
        if idx in _peak_select_indices:
            _peak_select_indices.discard(idx)
        else:
            _peak_select_indices.add(idx)
        _update_sel_series()
        _refresh_selected_table()

    _close_peak_select_window()

    dpg.add_window(
        tag=PEAK_SELECT_WINDOW_TAG,
        label="Select DRT Peaks: " + config.display_file,
        modal=True,
        width=1200,
        height=700,
        no_collapse=True,
        no_resize=False,
    )

    dpg.add_group(parent=PEAK_SELECT_WINDOW_TAG, tag="cnls_peak_select_group", horizontal=True)
    dpg.add_child_window(parent="cnls_peak_select_group", tag="cnls_peak_select_left", width=420, height=-55, border=True)
    dpg.add_child_window(parent="cnls_peak_select_group", tag="cnls_peak_select_right", width=-1, height=-55, border=True)

    # ---- LEFT: selected points only ----
    dpg.add_text(parent="cnls_peak_select_left", default_value="Click points on the plot to select.")
    dpg.add_table(
        parent="cnls_peak_select_left",
        tag="cnls_peak_select_table",
        header_row=True,
        resizable=True,
        scrollX=True,
        scrollY=True,
        borders_innerV=True,
        borders_outerV=True,
        borders_outerH=True,
        policy=dpg.mvTable_SizingFixedFit,
        height=-1,
    )
    dpg.add_table_column(parent="cnls_peak_select_table", label="Peak", width_fixed=True, init_width_or_weight=45)
    dpg.add_table_column(parent="cnls_peak_select_table", label="Freq [Hz]", width_fixed=True, init_width_or_weight=110)
    dpg.add_table_column(parent="cnls_peak_select_table", label="tau [s]", width_fixed=True, init_width_or_weight=110)
    dpg.add_table_column(parent="cnls_peak_select_table", label="gamma", width_fixed=True, init_width_or_weight=110)
    dpg.add_table_column(parent="cnls_peak_select_table", label="", width_fixed=True, init_width_or_weight=30)

    # ---- PLOT ----
    dpg.add_plot(parent="cnls_peak_select_right", tag="cnls_peak_select_plot", width=-1, height=-1, no_menus=False)
    dpg.add_plot_axis(dpg.mvXAxis, parent="cnls_peak_select_plot", tag="cnls_peak_select_x", label=x_label, log_scale=True)
    dpg.add_plot_axis(dpg.mvYAxis, parent="cnls_peak_select_plot", tag="cnls_peak_select_y", label="gamma [ohm·s·cm2]")
    # DRT drawn as a scatter-line (single line series with circle markers) so the
    # default palette keeps the original blue for DRT and orange for Selected.
    # Labels starting with "##" stay plotted but are hidden from the legend.
    dpg.add_line_series(x_vals.tolist(), drt.tolist(), parent="cnls_peak_select_y", tag="cnls_peak_select_series_drt_line", label="DRT")
    dpg.add_scatter_series([], [], parent="cnls_peak_select_y", tag="cnls_peak_select_series_sel", label="Selected")
    dpg.add_scatter_series([], [], parent="cnls_peak_select_y", tag="cnls_peak_select_series_ptr", label="##pointer")
    dpg.add_plot_legend(parent="cnls_peak_select_plot")

    # Show hollow circle markers on the DRT line and keep the Selected markers hollow,
    # leaving marker outline colors on the default palette (original blue / orange).
    with dpg.theme() as _drt_line_theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Circle, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
    with dpg.theme() as _sel_scatter_theme:
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
    dpg.bind_item_theme("cnls_peak_select_series_drt_line", _drt_line_theme)
    dpg.bind_item_theme("cnls_peak_select_series_sel", _sel_scatter_theme)

    dpg.add_text(parent="cnls_peak_select_right", default_value="Selected peaks: 0", tag="cnls_peak_select_count")
    dpg.add_text(parent="cnls_peak_select_right", default_value="Pointer -> Index: -", tag="cnls_peak_select_hover")

    dpg.add_handler_registry(tag=PEAK_SELECT_HANDLERS_TAG)
    dpg.add_mouse_move_handler(parent=PEAK_SELECT_HANDLERS_TAG, callback=lambda s, a: _hover())
    dpg.add_mouse_click_handler(parent=PEAK_SELECT_HANDLERS_TAG, button=dpg.mvMouseButton_Left, callback=lambda s, a: _toggle_nearest())

    _update_sel_series()
    _refresh_selected_table()
    dpg.fit_axis_data("cnls_peak_select_x")
    dpg.fit_axis_data("cnls_peak_select_y")

    # ---- Buttons ----
    dpg.add_separator(parent=PEAK_SELECT_WINDOW_TAG)
    dpg.add_group(parent=PEAK_SELECT_WINDOW_TAG, tag="cnls_peak_select_buttons", horizontal=True)
    dpg.add_button(parent="cnls_peak_select_buttons", label="Apply selection", callback=lambda: _apply_peak_selection(config, f_drt))
    dpg.add_button(parent="cnls_peak_select_buttons", label="Clear", callback=lambda: (_peak_select_indices.clear(), _update_sel_series(), _refresh_selected_table()))
    dpg.add_button(parent="cnls_peak_select_buttons", label="Cancel", callback=lambda: _close_peak_select_window())


def _apply_peak_selection(config, f_drt):
    """Write the selected DRT points into the peak frequency list (ranked high->low)."""
    import src.GUI.Utils.progress_modal as _pm

    indices = sorted(_peak_select_indices)
    if not indices:
        _pm.show_warning_dialog(
            "CNLS — Select Peaks",
            "No DRT points selected. Please select at least one point."
        )
        return

    freqs = sorted((float(f_drt[i]) for i in indices), reverse=True)

    file_key = os.path.splitext(config.display_file)[0]
    CNLS_tmp = config.store[file_key]['CNLS']
    config.store["peak_fixed_frequencies"] = list(freqs)
    CNLS_tmp.f_fixed = list(freqs)
    CNLS_tmp.f_mode = "fixed"
    # Remember that this file has a user-applied selection so reopening the
    # window restores it instead of auto-clearing.
    config.store.setdefault("cnls_peaks_applied", set()).add(file_key)

    if dpg.does_item_exist("input_nbr_peaks"):
        dpg.set_value("input_nbr_peaks", len(freqs))
    dynamic_peak_ids(None, 0, config)

    _close_peak_select_window()
    print(f"---- {len(freqs)} peak frequencies set from DRT selection.")


def update_data_type(sender, appdata, config):
    """Update the data type for CNLS fitting.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    try:
        CNLS_tmp = config.store[file_name_no_ext]['CNLS']
        CNLS_tmp.data_type = normalize_cnls_data_type(appdata)
        EIS_tmp = config.store[file_name_no_ext]['EIS']
        apply_cnls_reference_data(CNLS_tmp, EIS_tmp)
        gui_utils.cnls_plots.update_single_plots(config)
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")
    
    print(f"---- Data type updated to {CNLS_tmp.data_type}.")

def nbr_iteration(sender, appdata, config):
    """Update the number of iterations for CNLS fitting.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    try:
        config.store[file_name_no_ext]['CNLS'].iteration = appdata
    except:
        raise ValueError("File does not exist or CNLS data is invalid.")
    
    print(f"---- Number of iterations updated to {appdata}.")

def segment_constraints(sender, appdata, config):
    """Update the segment constraints for CNLS fitting.
    """
    if appdata:
        config.store["segment_constraints"] = 'segment'
        dpg.configure_item("checkbox_cnls_R_percentage", enabled=True)
        dpg.configure_item("checkbox_cnls_Tau_percentage", enabled=True)
    else:
        config.store["segment_constraints"] = 'free'
        dpg.configure_item("checkbox_cnls_R_percentage", enabled=False)
        dpg.configure_item("checkbox_cnls_Tau_percentage", enabled=False)
    print(f"---- Segment constraints updated to {config.store['segment_constraints']}.")

# Update the element tables
def initialize_elements(config):
    """Update the initial elements for CNLS fitting.
    
    Args:
        config: Configuration object.
    """
    print("-- Initializing CNLS elements...")
    try:
        file_name_no_ext = os.path.splitext(config.display_file)[0]
        config.store['elements'] = config.store[file_name_no_ext]['CNLS'].Elements
        gui_utils.cnls_elements.initialize_element(config)
        print(f"---- CNLS elements initialization finished.")
    except:
        print("[Warning] No previous CNLS elements found.")


def _selector_add_element_callback(sender, appdata, user_data):
    """Quick-add one element from Selector window."""
    config, element_type = user_data
    _selector_add_element_to_buffer(config, element_type)
    refresh_selector_preview(config)
    refresh_selector_remove_window(config)


def _selector_get_elements(config):
    elements = config.store.get(CNLS_SELECTOR_EDIT_KEY)
    if isinstance(elements, list):
        return elements
    return config.store.get("Elements", [])


def _selector_start_session(config):
    config.store[CNLS_SELECTOR_EDIT_KEY] = copy.deepcopy(config.store.get("Elements", []))
    _selector_remove_selected_names.clear()


def _selector_end_session(config):
    if CNLS_SELECTOR_EDIT_KEY in config.store:
        del config.store[CNLS_SELECTOR_EDIT_KEY]
    _selector_remove_selected_names.clear()


def _selector_reindex_buffer_names(config):
    elements = config.store.get(CNLS_SELECTOR_EDIT_KEY, [])
    for i, element in enumerate(elements):
        et = element.get('type', 'Resistor')
        prefix = config.store.get('element_list', {}).get(et, et)
        element['name'] = f"{prefix}{i + 1}"


def _selector_add_element_to_buffer(config, element_type):
    if element_type not in _SELECTOR_PARAM_LIST:
        return
    buffer_elements = config.store.get(CNLS_SELECTOR_EDIT_KEY, [])
    param, ub, lb = _SELECTOR_PARAM_LIST[element_type]
    buffer_elements.append({
        'name': '',
        'type': element_type,
        'Param': copy.deepcopy(param),
        'Ub': copy.deepcopy(ub),
        'Lb': copy.deepcopy(lb),
    })
    _selector_reindex_buffer_names(config)


def _selector_toggle_remove_choice(sender, appdata, user_data):
    """Track multi-select state in remove window."""
    element_name = user_data
    if appdata:
        if element_name not in _selector_remove_selected_names:
            _selector_remove_selected_names.append(element_name)
    else:
        if element_name in _selector_remove_selected_names:
            _selector_remove_selected_names.remove(element_name)
    _update_remove_status_text()


def _update_remove_status_text():
    if not dpg.does_item_exist(CNLS_SELECTOR_REMOVE_STATUS_TAG):
        return
    if len(_selector_remove_selected_names) == 0:
        dpg.set_value(CNLS_SELECTOR_REMOVE_STATUS_TAG, "Selected: 0")
    else:
        dpg.set_value(
            CNLS_SELECTOR_REMOVE_STATUS_TAG,
            f"Selected: {len(_selector_remove_selected_names)}  ({', '.join(_selector_remove_selected_names)})",
        )


def _selector_remove_selected_callback(sender, appdata, config):
    """Remove all selected elements from Selector remove area."""
    if len(_selector_remove_selected_names) == 0:
        return

    names = [elem.get('name', '') for elem in _selector_get_elements(config)]
    remove_indices = sorted(
        [names.index(name) for name in _selector_remove_selected_names if name in names],
        reverse=True,
    )
    buffer_elements = config.store.get(CNLS_SELECTOR_EDIT_KEY, [])
    for idx in remove_indices:
        if idx < len(buffer_elements):
            del buffer_elements[idx]

    _selector_reindex_buffer_names(config)
    _selector_remove_selected_names.clear()
    refresh_selector_preview(config)
    refresh_selector_remove_window(config)


def refresh_selector_remove_window(config):
    """Refresh selectable element boxes in Selector remove area."""
    if not dpg.does_item_exist(CNLS_SELECTOR_REMOVE_LIST_TAG):
        return

    names = [elem.get('name', '') for elem in _selector_get_elements(config)]
    _selector_remove_selected_names[:] = [name for name in _selector_remove_selected_names if name in names]

    dpg.delete_item(CNLS_SELECTOR_REMOVE_LIST_TAG, children_only=True)
    with dpg.table(
        parent=CNLS_SELECTOR_REMOVE_LIST_TAG,
        header_row=False,
        borders_innerH=False,
        borders_outerH=False,
        borders_innerV=False,
        borders_outerV=False,
        policy=dpg.mvTable_SizingStretchSame,
    ):
        col_n = 6
        for _ in range(col_n):
            dpg.add_table_column()
        for i in range(0, len(names), col_n):
            with dpg.table_row():
                row_names = names[i:i + col_n]
                for name in row_names:
                    dpg.add_selectable(
                        label=name,
                        default_value=(name in _selector_remove_selected_names),
                        callback=_selector_toggle_remove_choice,
                        user_data=name,
                    )
                for _ in range(col_n - len(row_names)):
                    dpg.add_text("")

    _update_remove_status_text()


def _selector_confirm_callback(sender, appdata, config):
    """Apply Selector edits to CNLS parameter table and file CNLS objects."""
    edited = copy.deepcopy(config.store.get(CNLS_SELECTOR_EDIT_KEY, []))
    config.store["Elements"] = edited

    for _fn in config.selected_files:
        _fk = os.path.splitext(_fn)[0]
        if _fk in config.store and 'CNLS' in config.store[_fk]:
            config.store[_fk]['CNLS'].Elements = copy.deepcopy(edited)

    gui_utils.cnls_elements.update_elements(config)
    _selector_end_session(config)
    if dpg.does_item_exist(CNLS_SELECTOR_WINDOW_TAG):
        dpg.hide_item(CNLS_SELECTOR_WINDOW_TAG)


def _selector_cancel_callback(sender, appdata, config):
    """Discard Selector edits and close window."""
    _selector_end_session(config)
    if dpg.does_item_exist(CNLS_SELECTOR_WINDOW_TAG):
        dpg.hide_item(CNLS_SELECTOR_WINDOW_TAG)


def _draw_resistor(parent, x0, x1, y, color, thickness):
    width = max(12.0, x1 - x0)
    mid = (x0 + x1) / 2.0

    # Keep resistor leads around 15 px when space allows, while using a smaller body.
    lead_target = 15.0
    max_body_from_lead = max(8.0, width - 2.0 * lead_target)
    body_w = min(42.0, max(14.0, width * 0.34), max_body_from_lead)

    r0 = mid - body_w / 2.0
    r1 = mid + body_w / 2.0
    rect_h = min(7.0, max(4.6, body_w * 0.16))

    dpg.draw_line((x0, y), (r0, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((r1, y), (x1, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_rectangle((r0, y - rect_h), (r1, y + rect_h), color=color, fill=(35, 50, 66, 200), thickness=1.8, parent=parent)


def _draw_capacitor(parent, x0, x1, y, color, thickness):
    mid = (x0 + x1) / 2.0
    gap = min(7.0, max(4.0, (x1 - x0) / 6.0))
    plate_h = 16
    dpg.draw_line((x0, y), (mid - gap, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((mid - gap, y - plate_h), (mid - gap, y + plate_h), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((mid + gap, y - plate_h), (mid + gap, y + plate_h), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((mid + gap, y), (x1, y), color=color, thickness=thickness, parent=parent)


def _draw_inductor(parent, x0, x1, y, color, thickness):
    coil_count = 4
    span = max(20.0, x1 - x0)
    radius = span / (coil_count * 2.0)
    left = (x0 + x1) / 2.0 - coil_count * radius
    dpg.draw_line((x0, y), (left, y), color=color, thickness=thickness, parent=parent)
    for i in range(coil_count):
        cx = left + radius * (2 * i + 1)
        dpg.draw_circle((cx, y), radius, color=color, thickness=thickness, parent=parent)
    dpg.draw_line((left + coil_count * 2.0 * radius, y), (x1, y), color=color, thickness=thickness, parent=parent)


def _draw_warburg(parent, x0, x1, y, color, thickness):
    width = max(12.0, x1 - x0)
    lead = min(10.0, max(4.0, width * 0.14))
    w0 = x0 + lead
    w1 = x1 - lead
    amp = min(4.5, max(2.8, (w1 - w0) * 0.10))

    dpg.draw_line((x0, y), (w0, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((w1, y), (x1, y), color=color, thickness=thickness, parent=parent)

    segments = 6
    step = max(3.0, (w1 - w0) / segments)
    points = [(w0, y)]
    for i in range(1, segments + 1):
        px = w0 + i * step
        py = y + (amp if i % 2 else -amp)
        points.append((px, py))
    dpg.draw_polyline(points, color=color, thickness=thickness, parent=parent)


def _draw_generic_block(parent, x0, x1, y, color, fill):
    dpg.draw_rectangle((x0, y - 13), (x1, y + 13), color=color, fill=fill, thickness=1.5, parent=parent)


def _draw_label_block(parent, x0, x1, y, color, fill, label):
    _draw_generic_block(parent, x0, x1, y, color, fill)
    tx = (x0 + x1) / 2.0 - 5
    dpg.draw_text((tx, y - 7), str(label), color=(230, 240, 248, 255), parent=parent, size=13)


def _estimate_text_width(label, font_size):
    """Estimate text width for drawlist labels without requiring font metrics API."""
    width_units = 0.0
    for ch in str(label):
        if ch in "WwMm@#%&":
            width_units += 0.88
        elif ch in "firtjlI1|":
            width_units += 0.38
        elif ch.isupper():
            width_units += 0.66
        elif ch.islower():
            width_units += 0.56
        elif ch.isdigit():
            width_units += 0.58
        else:
            width_units += 0.60
    return max(6.0, width_units * float(font_size))


def _draw_abbrev_series(parent, x0, x1, y, color, label, thickness=2):
    """Draw a series abbreviation (e.g., W, G) without any surrounding box."""
    width = max(12.0, x1 - x0)
    # Match the Q-style connector behavior: target 15 px lead with safe fallback.
    min_inner_span = 6.0
    max_lead = max(2.0, (width - min_inner_span) / 2.0)
    lead = min(max_lead, max(15.0, width * 0.20))
    t0 = x0 + lead
    t1 = x1 - lead

    dpg.draw_line((x0, y), (t0, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((t1, y), (x1, y), color=color, thickness=thickness, parent=parent)

    label_str = str(label)
    inner_span = max(8.0, t1 - t0)
    if label_str in ["W", "G", "FLW", "fFLW"]:
        factor = 0.52 if label_str == "W" else 0.56
        font_size = int(max(18, min(24, inner_span * factor)))
    elif len(label_str) <= 2:
        font_size = int(max(16, min(22, inner_span * 0.40)))
    elif len(label_str) <= 4:
        font_size = int(max(14, min(19, inner_span * 0.31)))
    else:
        font_size = int(max(12, min(17, inner_span * 0.25)))

    # Prefer measured text width for visual centering; fallback to estimator.
    text_w = _estimate_text_width(label_str, font_size)
    try:
        measured = dpg.get_text_size(label_str)
        if isinstance(measured, (list, tuple)) and len(measured) >= 1:
            text_w = max(1.0, float(measured[0]))
    except Exception:
        pass
    tx = (x0 + x1) / 2.0 - text_w / 2.0
    ty = y - font_size * 0.46
    dpg.draw_text((tx, ty), label_str, color=(230, 240, 248, 255), parent=parent, size=font_size)


def _draw_cpe_symbol(parent, x0, x1, y, color, thickness):
    """Draw CPE symbol as two chevron-like folded lines (<< style), no text."""
    width = max(14.0, x1 - x0)
    # Keep a clearly visible side lead while preserving enough inner span for the chevrons.
    min_inner_span = 6.0
    max_lead = max(2.0, (width - min_inner_span) / 2.0)
    lead = min(max_lead, max(15.0, width * 0.20))
    c0 = x0 + lead
    c1 = x1 - lead
    dpg.draw_line((x0, y), (c0, y), color=color, thickness=thickness, parent=parent)
    dpg.draw_line((c1, y), (x1, y), color=color, thickness=thickness, parent=parent)

    span = max(10.0, c1 - c0)
    # Use a taller and slightly narrower fold so the chevrons look less sharp.
    h = min(6.8, max(4.2, span * 0.19))
    left_center = c0 + span * 0.40
    right_center = c0 + span * 0.60
    half = max(2.4, span * 0.10)

    # Two compact, symmetric chevrons for a cleaner << appearance.
    dpg.draw_polyline(
        [(left_center + half, y - h), (left_center - half, y), (left_center + half, y + h)],
        color=color,
        thickness=thickness,
        parent=parent,
    )
    dpg.draw_polyline(
        [(right_center + half, y - h), (right_center - half, y), (right_center + half, y + h)],
        color=color,
        thickness=thickness,
        parent=parent,
    )


def _draw_parallel_branch(parent, x0, x1, y, color, fill, lower_type):
    """Draw a two-branch parallel network between left/right nodes."""
    top_y = y - 16
    bot_y = y + 16

    dpg.draw_line((x0, top_y), (x0, bot_y), color=color, thickness=2, parent=parent)
    dpg.draw_line((x1, top_y), (x1, bot_y), color=color, thickness=2, parent=parent)
    dpg.draw_circle((x0, y), 1.8, color=color, fill=color, thickness=1, parent=parent)
    dpg.draw_circle((x1, y), 1.8, color=color, fill=color, thickness=1, parent=parent)

    # Upper branch: resistor
    _draw_resistor(parent, x0, x1, top_y, color, 2)

    # Lower branch: depends on element family
    if lower_type == "capacitor":
        _draw_capacitor(parent, x0, x1, bot_y, color, 2)
    elif lower_type == "cpe":
        _draw_cpe_symbol(parent, x0, x1, bot_y, color, 2)
    elif lower_type == "label_w":
        _draw_label_block(parent, x0 + 4, x1 - 4, bot_y, color, fill, "W")
    elif lower_type == "label_g":
        _draw_label_block(parent, x0 + 4, x1 - 4, bot_y, color, fill, "G")
    else:
        _draw_generic_block(parent, x0 + 4, x1 - 4, bot_y, color, fill)


def _draw_randle_symbol(parent, x0, x1, y, color, fill, cpe=False, warburg_is_fractal=False):
    """Draw Randle family as: (C/CPE) || (R + FLW/fFLW)."""
    width = max(44.0, x1 - x0)
    lead = min(8.0, max(4.0, width * 0.08))
    core0 = x0 + lead
    core1 = x1 - lead
    core_w = max(24.0, core1 - core0)

    top_y = y - 16
    bot_y = y + 16

    dpg.draw_line((x0, y), (core0, y), color=color, thickness=2, parent=parent)
    dpg.draw_line((core1, y), (x1, y), color=color, thickness=2, parent=parent)

    # Parallel rails (left/right nodes)
    dpg.draw_line((core0, top_y), (core0, bot_y), color=color, thickness=2, parent=parent)
    dpg.draw_line((core1, top_y), (core1, bot_y), color=color, thickness=2, parent=parent)
    dpg.draw_circle((core0, y), 1.8, color=color, fill=color, thickness=1, parent=parent)
    dpg.draw_circle((core1, y), 1.8, color=color, fill=color, thickness=1, parent=parent)

    # Upper branch: C or CPE
    if cpe:
        _draw_cpe_symbol(parent, core0, core1, top_y, color, 2)
    else:
        _draw_capacitor(parent, core0, core1, top_y, color, 2)

    # Lower branch: series R + FLW/fFLW
    r_end = core0 + core_w * 0.46
    w_start = r_end + core_w * 0.08
    _draw_resistor(parent, core0, r_end, bot_y, color, 2)
    dpg.draw_line((r_end, bot_y), (w_start, bot_y), color=color, thickness=2, parent=parent)
    if w_start < core1 - 2:
        warburg_label = "fFLW" if warburg_is_fractal else "FLW"
        _draw_abbrev_series(parent, w_start, core1, bot_y, color, warburg_label, thickness=2)
    else:
        dpg.draw_line((w_start, bot_y), (core1, bot_y), color=color, thickness=2, parent=parent)


def _draw_element_symbol(parent, element_type, x0, x1, y, color, fill):
    # Make symbols a bit more compact so connectors between elements are clearer.
    sx0, sx1 = x0, x1
    width = max(1.0, x1 - x0)
    pad = min(8.0, max(2.0, width * 0.08))
    x0 = x0 + pad
    x1 = x1 - pad

    # Keep the compact symbol electrically connected to the outer chain wire.
    dpg.draw_line((sx0, y), (x0, y), color=color, thickness=2, parent=parent)
    dpg.draw_line((x1, y), (sx1, y), color=color, thickness=2, parent=parent)

    thickness = 2
    et = str(element_type)
    if et == "Resistor":
        _draw_resistor(parent, x0, x1, y, color, thickness)
    elif et == "RC":
        _draw_parallel_branch(parent, x0, x1, y, color, fill, lower_type="capacitor")
    elif et == "RQ":
        _draw_parallel_branch(parent, x0, x1, y, color, fill, lower_type="cpe")
    elif et == "Gerisher":
        _draw_abbrev_series(parent, x0, x1, y, color, "G", thickness=thickness)
    elif et == "FLW":
        _draw_abbrev_series(parent, x0, x1, y, color, "FLW", thickness=thickness)
    elif et == "fFLW":
        _draw_abbrev_series(parent, x0, x1, y, color, "fFLW", thickness=thickness)
    elif et in ["Capacitor", "CPE"]:
        if et == "CPE":
            _draw_cpe_symbol(parent, x0, x1, y, color, thickness)
        else:
            _draw_capacitor(parent, x0, x1, y, color, thickness)
    elif et in ["Inductor", "Inductor_a"]:
        _draw_inductor(parent, x0, x1, y, color, thickness)
    elif et == "Warburg":
        _draw_abbrev_series(parent, x0, x1, y, color, "W", thickness=thickness)
    elif et == "RandleC":
        _draw_randle_symbol(parent, x0, x1, y, color, fill, cpe=False, warburg_is_fractal=False)
    elif et == "RandleCPE":
        _draw_randle_symbol(parent, x0, x1, y, color, fill, cpe=True, warburg_is_fractal=False)
    elif et == "RandleCfFLW":
        _draw_randle_symbol(parent, x0, x1, y, color, fill, cpe=False, warburg_is_fractal=True)
    elif et == "RandleCPEfFLW":
        _draw_randle_symbol(parent, x0, x1, y, color, fill, cpe=True, warburg_is_fractal=True)
    else:
        _draw_generic_block(parent, x0, x1, y, color, fill)


def refresh_selector_preview(config):
    """Refresh equivalent-circuit preview in Selector window."""
    if not dpg.does_item_exist(CNLS_SELECTOR_DRAWLIST_TAG):
        return

    dpg.delete_item(CNLS_SELECTOR_DRAWLIST_TAG, children_only=True)
    elements = _selector_get_elements(config)
    if not isinstance(elements, list) or len(elements) == 0:
        dpg.draw_text((20, 45), "No elements. Use add buttons above.", color=(190, 190, 190, 255), parent=CNLS_SELECTOR_DRAWLIST_TAG, size=16)
        return

    draw_w = 1040
    draw_h = 220
    if dpg.does_item_exist(CNLS_SELECTOR_DRAWLIST_TAG):
        try:
            rect_size = dpg.get_item_rect_size(CNLS_SELECTOR_DRAWLIST_TAG)
            if isinstance(rect_size, (list, tuple)) and len(rect_size) >= 1:
                draw_w = max(760, int(rect_size[0]))
                if len(rect_size) >= 2:
                    draw_h = max(150, int(rect_size[1]))
        except Exception:
            pass

    n = len(elements)
    # Adaptive sizing keeps symbol proportions readable across resolutions.
    scale_x = draw_w / 1040.0
    scale_y = draw_h / 220.0
    scale = max(0.85, min(1.8, min(scale_x, scale_y)))

    margin = max(14.0, min(40.0, 24.0 * scale))
    lead = max(16.0, min(44.0, 22.0 * scale))
    gap = max(10.0, min(30.0, 18.0 * scale))
    wire_thickness = max(1.6, min(3.2, 2.0 * scale))

    usable = draw_w - 2 * margin - 2 * lead
    element_units = [2.0 if str(elem.get("type", "")).startswith("Randle") else 1.0 for elem in elements]
    total_units = max(1.0, float(sum(element_units)))
    symbol_span_raw = (usable - gap * (n - 1)) / total_units
    symbol_span_min = max(30.0, 34.0 * scale * 0.92)
    symbol_span_max = max(78.0, 102.0 * scale)
    symbol_span = min(symbol_span_max, max(symbol_span_min, symbol_span_raw))

    top_pad = max(14.0, min(34.0, 20.0 * scale))
    label_font = int(max(12, min(18, round(14 * scale))))
    label_gap = max(34.0, symbol_span * 0.52, label_font * 2.35)
    mid_y = max(top_pad + 22.0, min(draw_h - label_gap - label_font - 10.0, draw_h * 0.46))

    wire_color = (195, 195, 195, 255)
    symbol_color = (94, 170, 220, 255)
    symbol_fill = (25, 41, 52, 180)

    start_x = margin
    dpg.draw_line((start_x, mid_y), (start_x + lead, mid_y), color=wire_color, thickness=wire_thickness, parent=CNLS_SELECTOR_DRAWLIST_TAG)

    cursor_x = start_x + lead
    for idx, element in enumerate(elements):
        element_name = str(element.get("name", f"E{idx + 1}"))
        element_type = str(element.get("type", "Unknown"))
        element_span = symbol_span * element_units[idx]
        x0 = cursor_x
        x1 = cursor_x + element_span
        _draw_element_symbol(CNLS_SELECTOR_DRAWLIST_TAG, element_type, x0, x1, mid_y, symbol_color, symbol_fill)
        label_w = max(18.0, len(element_name) * (label_font * 0.52))
        label_x = (x0 + x1) / 2.0 - label_w / 2.0
        label_y = min(draw_h - label_font - 6.0, mid_y + label_gap)
        dpg.draw_text((label_x, label_y), element_name, color=(225, 235, 245, 255), parent=CNLS_SELECTOR_DRAWLIST_TAG, size=label_font)

        right_x = x1
        next_x = right_x + gap
        dpg.draw_line((right_x, mid_y), (next_x, mid_y), color=wire_color, thickness=wire_thickness, parent=CNLS_SELECTOR_DRAWLIST_TAG)

        cursor_x = next_x

    dpg.draw_line((cursor_x, mid_y), (cursor_x + lead, mid_y), color=wire_color, thickness=wire_thickness, parent=CNLS_SELECTOR_DRAWLIST_TAG)

def open_selector_window(sender, appdata, config):
    """Open circuit selector window with quick-add buttons and a live preview."""
    _ensure_store_elements(config)
    _selector_start_session(config)

    if dpg.does_item_exist(CNLS_SELECTOR_WINDOW_TAG):
        dpg.show_item(CNLS_SELECTOR_WINDOW_TAG)
        refresh_selector_preview(config)
        refresh_selector_remove_window(config)
        return

    vp_w = dpg.get_viewport_client_width() if hasattr(dpg, "get_viewport_client_width") else dpg.get_viewport_width()
    vp_h = dpg.get_viewport_client_height() if hasattr(dpg, "get_viewport_client_height") else dpg.get_viewport_height()
    win_width = min(max(980, int(vp_w * 0.86)), max(760, vp_w - 20))
    win_height = min(max(620, int(vp_h * 0.88)), max(520, vp_h - 20))

    add_h = 130
    remove_h = 150
    action_h = 56
    fixed_overhead = 210
    preview_h = max(170, win_height - (add_h + remove_h + action_h + fixed_overhead))

    with dpg.window(
        tag=CNLS_SELECTOR_WINDOW_TAG,
        label="CNLS Selector",
        modal=True,
        width=win_width,
        height=win_height,
        pos=(max(0, (vp_w - win_width) // 2), max(0, (vp_h - win_height) // 2)),
        no_resize=True,
        no_scrollbar=True,
        no_collapse=True,
    ):
        dpg.add_text("Add Elements")
        with dpg.child_window(height=add_h, border=True, no_scrollbar=True):
            with dpg.table(
                tag=CNLS_SELECTOR_ADD_TABLE_TAG,
                header_row=False,
                borders_innerH=False,
                borders_outerH=False,
                borders_innerV=False,
                borders_outerV=False,
                policy=dpg.mvTable_SizingStretchSame,
            ):
                col_n = 5
                for _ in range(col_n):
                    dpg.add_table_column()

                element_types = list(config.store.get("element_list", {}).keys())
                for i in range(0, len(element_types), col_n):
                    with dpg.table_row():
                        row_types = element_types[i:i + col_n]
                        for et in row_types:
                            dpg.add_button(
                                label=et,
                                width=-1,
                                callback=_selector_add_element_callback,
                                user_data=(config, et),
                            )
                        for _ in range(col_n - len(row_types)):
                            dpg.add_text("")

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=6)

        dpg.add_text("Remove Elements")
        with dpg.child_window(height=remove_h, border=True, no_scrollbar=True):
            dpg.add_text(tag=CNLS_SELECTOR_REMOVE_STATUS_TAG, default_value="Selected: 0")
            with dpg.child_window(tag=CNLS_SELECTOR_REMOVE_LIST_TAG, height=75, border=True, no_scrollbar=True):
                pass
            with dpg.group(horizontal=True):
                dpg.add_button(label="Remove Selected", width=180, callback=_selector_remove_selected_callback, user_data=config)

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=6)

        dpg.add_text("Equivalent Circuit Preview")
        with dpg.child_window(height=preview_h, horizontal_scrollbar=False, border=True):
            dpg.add_drawlist(tag=CNLS_SELECTOR_DRAWLIST_TAG, width=1200, height=240)

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=6)
        with dpg.child_window(height=action_h, border=True, no_scrollbar=True):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Confirm", width=180, callback=_selector_confirm_callback, user_data=config)
                dpg.add_button(label="Cancel", width=180, callback=_selector_cancel_callback, user_data=config)

    refresh_selector_remove_window(config)
    refresh_selector_preview(config)

def _apply_rc_fit_initialization(CNLS_tmp):
    rc_cnls = copy.deepcopy(CNLS_tmp)
    rc_counter = 3

    for element in rc_cnls.Elements:
        if element.get('name') in ['L1', 'R2']:
            continue

        element['name'] = f"RC{rc_counter}"
        element['type'] = 'RC'

        if isinstance(element.get('Param'), list) and len(element['Param']) > 2:
            del element['Param'][2]
        if isinstance(element.get('Ub'), list) and len(element['Ub']) > 2:
            del element['Ub'][2]
        if isinstance(element.get('Lb'), list) and len(element['Lb']) > 2:
            del element['Lb'][2]
        rc_counter += 1

    # Run one RC-equivalent fit and print residual metrics.
    for i in range(0, CNLS_tmp.iteration):
        print(f'---- RC fit iteration {i+1}/{CNLS_tmp.iteration}...')
        rc_cnls.FitCircuit()

    # Write fitted RC values back using extracted parameter arrays.
    for idx in range(len(CNLS_tmp.Elements)):
        src_start = rc_cnls.ElementsStartIndex[idx]
        src_end = rc_cnls.ElementsEndIndex[idx] + 1

        src_param = [float(v) for v in rc_cnls.ElementsParamValues[src_start:src_end]]
        src_ub = [float(v) for v in rc_cnls.UpperBound[src_start:src_end]]
        src_lb = [float(v) for v in rc_cnls.LowerBound[src_start:src_end]]

        if CNLS_tmp.Elements[idx]['name'] in ['L1', 'R2']:
            CNLS_tmp.Elements[idx]['Param'] = src_param
            CNLS_tmp.Elements[idx]['Ub'] = src_ub
            CNLS_tmp.Elements[idx]['Lb'] = src_lb
        else:
            CNLS_tmp.Elements[idx]['Param'][:2] = src_param[:2]
            CNLS_tmp.Elements[idx]['Ub'][:2] = src_ub[:2]
            CNLS_tmp.Elements[idx]['Lb'][:2] = src_lb[:2]

    CNLS_tmp.ElementsNames = []
    CNLS_tmp.initialize_elements(change_UBLB=True)

    return CNLS_tmp
    
# Initialize the CNLS element parameters
def initialize_parameters(sender, appdata, config):
    """Initialize the CNLS element parameters."""
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "CNLS — Initialize Parameters", "Initializing CNLS parameters...",
        max(1, len(config.selected_files)),
    )
    _ensure_store_elements(config)
    names = [elem.get('name', '') for elem in config.store['Elements'][:]]
    has_randle = any('Randle' in name for name in names)
    if has_randle:
        dpg.configure_item("checkbox_cnls_segement_constraints", default_value=False, enabled=False)
        config.store["segment_constraints"] = 'free'
        print('---- Segment constraints set to free due to the presence of Randle elements.')

    # Snapshot UI state once. Do not restore UI values during initialization.
    rs_lb_kk = dpg.get_value("check_box_cnls_rs_lb_kk") if dpg.does_item_exist("check_box_cnls_rs_lb_kk") else False
    rs_lb_drt = dpg.get_value("check_box_cnls_rs_lb_drt") if dpg.does_item_exist("check_box_cnls_rs_lb_drt") else False
    
    # Load all the parameters from the CNLS setup
    _success = False
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            else:
                EIS_tmp = config.store[file_name_no_ext]['EIS']
            cnls_existing = config.store[file_name_no_ext].get('CNLS', None)
            need_rebuild_cnls = (
                cnls_existing is None
                or cnls_existing.DRTmes is None
                or not isinstance(cnls_existing.Elements, list)
                or len(cnls_existing.Elements) == 0
                or cnls_existing.DRTparameters is None
                or cnls_existing.DRTparameters['tknv_pos'] != EIS_tmp.parameter['DRT']['tknv_pos']
            )
            if need_rebuild_cnls:
                config.store[file_name_no_ext]['CNLS'] = copy.deepcopy(Circuit(
                    file_folder=config.folder_path,
                    filename=file_name,
                    Elements=copy.deepcopy(config.store['Elements']),
                    EIS=EIS_tmp,
                    data_type=normalize_cnls_data_type(dpg.get_value('combo_cnls_data_type'))
                ))
            
            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            CNLS_tmp.DRTparameters = EIS_tmp.parameter['DRT']
            CNLS_tmp.DRTparameters_rbf = EIS_tmp.parameter.get('DRT_RBF', None) if isinstance(EIS_tmp.parameter, dict) else None
            
            if not isinstance(CNLS_tmp.Elements, list) or len(CNLS_tmp.Elements) == 0:
                CNLS_tmp.Elements = copy.deepcopy(config.store['Elements'])
            if not isinstance(CNLS_tmp.Elements, list) or len(CNLS_tmp.Elements) == 0:
                raise ValueError("CNLS elements are empty. Please initialize circuit elements first.")

            reference = apply_cnls_reference_data(CNLS_tmp, EIS_tmp)
            # RL parameters (Rs, L, Rp) must always come from the tknv key of each
            # file's own EIS_tmp — same as pre-v3.27 code.  Using reference["drt_rl_result"]
            # is unreliable: for RBF data types the drt_rl_key has no "RL" subdict.
            _rl_base = CNLS_tmp.data_type.replace('_KK', '').replace('_DRT', '').replace('_RBF', '')
            try:
                rl_data = EIS_tmp['tknv_' + _rl_base].get('RL', {}) or {}
            except Exception:
                rl_data = {}

            CNLS_tmp.iteration = dpg.get_value('input_nbr_iters')
            CNLS_tmp.f_fixed = config.store["peak_fixed_frequencies"]
            CNLS_tmp.f_mode = "fixed"
            CNLS_tmp.constraint_type = config.store["segment_constraints"]
            CNLS_tmp.R_cons = None if not dpg.get_value("checkbox_cnls_R_percentage") else dpg.get_value("input_constraints_R_percentage")
            CNLS_tmp.Tau_cons = None if not dpg.get_value("checkbox_cnls_Tau_percentage") else dpg.get_value("input_constraints_Tau_percentage")
            # Disable RC_fit_switch if Randle elements exist
            has_randle = any('Randle' in element.get('type', '') for element in (CNLS_tmp.Elements or []))
            if has_randle:
                CNLS_tmp.RC_fit_switch = False
            else:
                config.store["RC_fit_switch"] = dpg.get_value("check_box_cnls_rc_initialization")
                CNLS_tmp.RC_fit_switch = config.store.get("RC_fit_switch", False)

            _orig_drtmes = CNLS_tmp.DRTmes
            # NO longer use abs(DRTmes); analyze DRT as-is
            R_est, freq_est, alpha_est, nbr_peaks, tau_est = CNLS_tmp.PeakDerivative(CNLS_tmp.f_mode, f_fixed=CNLS_tmp.f_fixed, nbr_peaks_fixed=len(CNLS_tmp.f_fixed))
            R_est_sum = np.sum(R_est)
            rp_reim = rl_data.get('Rp_ReIm', None)
            if rp_reim is not None and R_est_sum not in [None, 0]:
                R_est = R_est * rp_reim / R_est_sum
            param_list = list(zip(R_est, tau_est, alpha_est))
            param_list = [[float(x) for x in tup] for tup in param_list]
            
            # try:
            for idx, element in enumerate(CNLS_tmp.Elements):
                if element['name'] == 'L1':
                    if rl_data.get('L_ReIm', None) is not None:
                        CNLS_tmp.Elements[0]['Param'] = [float(rl_data['L_ReIm'])]
                elif element['name'] == 'R2':
                    if rl_data.get('Rs_ReIm', None) is not None:
                        CNLS_tmp.Elements[1]['Param'] = [float(rl_data['Rs_ReIm'])]
                elif element['type'] not in ['Capacitor', 'CPE'] and not 'Randle' in element['name']:
                    CNLS_tmp.Elements[idx]['Param'] = param_list[0][:len(CNLS_tmp.Elements[idx]['Param'])]
                    param_list.remove(param_list[0])
                elif 'Randle' in element['name']:
                    if element['type'] == 'RandleC':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][2:] = param_list[0][:2]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCPE':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        CNLS_tmp.Elements[idx]['Param'][2] = param_list[0][2]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][3:] = param_list[0][:2]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCPEfFLW':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        CNLS_tmp.Elements[idx]['Param'][2] = param_list[0][2]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][3:] = param_list[0][:3]
                        param_list.remove(param_list[0])
                    elif element['type'] == 'RandleCfFLW':
                        CNLS_tmp.Elements[idx]['Param'][:1] = param_list[0][:1]
                        param_list.remove(param_list[0])
                        CNLS_tmp.Elements[idx]['Param'][2:] = param_list[0][:3]
                        param_list.remove(param_list[0])
                else:
                    raise ValueError(f"SOCEIS now does not support with {element['type']} for automatic initialization, please use the maunal mode")
            # except:
            #     raise ValueError("The number of initial guess does not match the number of elements.")
                
            if len(param_list) != 0:
                raise ValueError("The number of initial guess is more than the number of elements.")
            
            # Store Rs_LB settings in CNLS object
            CNLS_tmp.Rs_LB_KK = rs_lb_kk
            CNLS_tmp.Rs_LB_DRT = rs_lb_drt
            
            r2_idx = None
            rs_value = None
            
            if rs_lb_kk or rs_lb_drt:
                # Find R2 element
                for idx, element in enumerate(CNLS_tmp.Elements):
                    if element['name'] == 'R2':
                        r2_idx = idx
                        break
                
                if r2_idx is not None:
                    # Priority: KK first, then DRT
                    if rs_lb_kk:
                        try:
                            if EIS_tmp.KK_data is not None and EIS_tmp.KK_data.get('res_ohm_kk') is not None:
                                rs_value = float(EIS_tmp.KK_data['res_ohm_kk'].item())
                        except Exception:
                            pass
                    
                    if rs_value is None and rs_lb_drt:
                        try:
                            # Prefer the already-resolved RL dict used above for CNLS init.
                            if rl_data.get('Rs_ReIm') is not None:
                                rs_value = float(rl_data['Rs_ReIm'])
                            else:
                                # Fallback: scan all tknv_* branches for RL.Rs_ReIm.
                                for _k, _v in EIS_tmp.items():
                                    if isinstance(_k, str) and _k.startswith('tknv_') and isinstance(_v, dict):
                                        _rl = _v.get('RL', {}) or {}
                                        if _rl.get('Rs_ReIm') is not None:
                                            rs_value = float(_rl['Rs_ReIm'])
                                            break
                        except Exception:
                            pass
                    
                    if rs_value is not None and rs_value > 0:
                        CNLS_tmp.Elements[r2_idx]['Lb'] = [rs_value]
            
            CNLS_tmp.initialize_elements()
            if CNLS_tmp.RC_fit_switch:
                CNLS_tmp = _apply_rc_fit_initialization(CNLS_tmp)
                config.store["Elements"] = CNLS_tmp.Elements

            constraint_percentage(CNLS_tmp)
            
            # Reapply Rs_LB after constraint_percentage (in case R_cons overwrote it)
            if (rs_lb_kk or rs_lb_drt) and r2_idx is not None and rs_value is not None and rs_value > 0:
                # Find the Rs parameter index using R2 element's start index
                if r2_idx < len(CNLS_tmp.ElementsStartIndex):
                    rs_param_idx = CNLS_tmp.ElementsStartIndex[r2_idx]
                    if rs_param_idx < len(CNLS_tmp.LowerBound):
                        CNLS_tmp.LowerBound[rs_param_idx] = rs_value
                        CNLS_tmp.Elements[r2_idx]['Lb'] = [rs_value]
            
            _pm.update_progress(progress, i + 1, file_name)
        _success = True
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] CNLS initialize_parameters:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("CNLS — Initialize Parameters Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)
    if not _success:
        return
    
    # Update display_file's Elements with Rs_LB applied
    display_key = os.path.splitext(config.display_file)[0] if config.display_file else None
    if display_key in config.store and 'CNLS' in config.store[display_key] and isinstance(config.store[display_key]['CNLS'].Elements, list):
        config.store["Elements"] = config.store[display_key]['CNLS'].Elements
    else:
        _ensure_store_elements(config)
    
    gui_utils.cnls_elements.update_elements(config)

# Load the parameters for the CNLS fitting
def load_parameters(sender, appdata, config):
    """Load the parameters for CNLS fitting."""
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "CNLS — Load Parameters", "Loading CNLS parameters...",
        max(1, len(config.selected_files)),
    )
    _ensure_store_elements(config)
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            if not isinstance(CNLS_tmp.Elements, list) or len(CNLS_tmp.Elements) == 0:
                CNLS_tmp.Elements = copy.deepcopy(config.store['Elements'])
            if not isinstance(CNLS_tmp.Elements, list) or len(CNLS_tmp.Elements) == 0:
                raise ValueError("CNLS elements are empty. Please initialize circuit elements first.")
            if dpg.does_item_exist("check_box_cnls_rs_lb_kk"):
                dpg.set_value("check_box_cnls_rs_lb_kk", bool(getattr(CNLS_tmp, "Rs_LB_KK", False)))
            if dpg.does_item_exist("check_box_cnls_rs_lb_drt"):
                dpg.set_value("check_box_cnls_rs_lb_drt", bool(getattr(CNLS_tmp, "Rs_LB_DRT", False)))
            CNLS_tmp.iteration = dpg.get_value('input_nbr_iters')
            CNLS_tmp.f_fixed = config.store["peak_fixed_frequencies"]
            CNLS_tmp.f_mode = "fixed"
            CNLS_tmp.RC_fit_switch = dpg.get_value("check_box_cnls_rc_initialization")
            CNLS_tmp.R_cons = None if not dpg.get_value("checkbox_cnls_R_percentage") else dpg.get_value("input_constraints_R_percentage")
            CNLS_tmp.Tau_cons = None if not dpg.get_value("checkbox_cnls_Tau_percentage") else dpg.get_value("input_constraints_Tau_percentage")
            CNLS_tmp.constraint_type = config.store["segment_constraints"]
            CNLS_tmp.ElementsNames = []
            CNLS_tmp.data_type = normalize_cnls_data_type(dpg.get_value('combo_cnls_data_type'))
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            apply_cnls_reference_data(CNLS_tmp, EIS_tmp)
            CNLS_tmp.initialize_elements(change_UBLB=False)
            _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] CNLS load_parameters:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("CNLS — Load Parameters Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

# Run the CNLS fitting
def cnls_fit(sender, appdata, config):
    import src.GUI.Utils.progress_modal as _pm
    total_iters = sum(
        config.store[os.path.splitext(f)[0]]['CNLS'].iteration
        for f in config.selected_files
        if os.path.splitext(f)[0] in config.store
        and 'CNLS' in config.store[os.path.splitext(f)[0]]
    ) or max(1, len(config.selected_files))
    progress = _pm.open_progress(
        "CNLS — Fit", "Running CNLS fit...", total_iters,
    )
    step = 0
    _success = False
    _current_file = ""
    try:
        for file_name in config.selected_files:
            _current_file = file_name
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            CNLS_tmp = config.store[file_name_no_ext]['CNLS']
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            apply_cnls_reference_data(CNLS_tmp, EIS_tmp)
            for iter_i in range(CNLS_tmp.iteration):
                _pm.update_progress(progress, step, f"{file_name_no_ext}  iter {iter_i + 1}/{CNLS_tmp.iteration}")
                CNLS_tmp.FitCircuit()
                step += 1
                _pm.update_progress(progress, step, f"{file_name_no_ext}  iter {iter_i + 1}/{CNLS_tmp.iteration}")
            CNLS_tmp.EvaluateCircuitDRT()
        _success = True
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] CNLS cnls_fit:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("CNLS — Fit Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)
    if not _success:
        return
    try:
        gui_utils.cnls_table.table_update(config)
        gui_utils.cnls_plots.update_single_plots(config)
        gui_utils.cnls_plots.update_all_plots(config)
    except Exception as _ep:
        import traceback as _tb
        print(f"[Warning] CNLS post-fit update failed:\n{_tb.format_exc()}")
        _pm.show_error_dialog("CNLS — Post-Fit Update Warning", f"{type(_ep).__name__}: {_ep}")

# Save the CNLS fitting results
def save_cnls(sender, appdata, config, CNLS):
    """Save the CNLS fitting results."""
    import src.GUI.Utils.progress_modal as _pm
    n = len(config.selected_files) if config.selected_files else 0
    progress = _pm.open_progress(
        "CNLS — Save", "Saving CNLS results...", max(1, n),
    )
    try:
        CNLS.backup_folder_to_temp_zip('CNLS', 'CNLS_backup.zip')
        _current_file = ""
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                raise FileNotFoundError('The specified file is not loaded or EIS processing is not done.')
            try:
                config.store[file_name_no_ext]['CNLS'].ExportCircuit()
            except Exception as _ei:
                import traceback as _tb
                print(f"[Warning] CNLS-save failed for {file_name}: {_ei}\n{_tb.format_exc()}")
                _pm.show_error_dialog("CNLS — Save Warning", f"'{file_name}' could not be saved:\n{_ei}")
            _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] CNLS save_cnls:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("CNLS — Save Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)