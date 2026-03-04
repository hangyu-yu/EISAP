import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
from src.Methods.DRT.DRT import DRT

def _get_manualcut_preview_data(config):
    """
    Preview for selector = RAW after ONLY upper/lower cut.
    No significance/outlier/KK/manual removal are applied here.

    This keeps selector indices stable and avoids misleading visuals.
    """
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    f = np.asarray(EIS_tmp.truncated["f"], dtype=float)
    Re = np.asarray(EIS_tmp.truncated["Re"], dtype=float)
    Im = np.asarray(EIS_tmp.truncated["Im"], dtype=float)

    return f, Re, Im

def parse_indices_1based_to_0based(text: str):
    if text is None:
        return []
    s = str(text).strip()
    if s == "" or s.lower() in {"n/a", "na", "none"}:
        return []

    out = []
    for token in s.replace(" ", "").split(","):
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            if a.isdigit() and b.isdigit():
                a, b = int(a), int(b)
                lo, hi = (a, b) if a <= b else (b, a)
                out.extend([i - 1 for i in range(lo, hi + 1) if i > 0])
        else:
            if token.isdigit():
                v = int(token)
                if v > 0:
                    out.append(v - 1)

    return sorted(set(out))

def open_manual_cut_window(config):
    if config.display_file in (None, "", []):
        return

    file_key = os.path.splitext(config.display_file)[0]
    if file_key not in config.store or "EIS" not in config.store[file_key]:
        return

    # close old one
    if dpg.does_item_exist("manual_cut_single_window"):
        close_manual_cut_window()

    # preview arrays
    f, Re, Im = _get_manualcut_preview_data(config)
    if f is None or len(f) == 0:
        return

    Re = np.asarray(Re, dtype=float)
    Im = np.asarray(Im, dtype=float)
    f = np.asarray(f, dtype=float)

    prev = set(config.store[file_key]["EIS"].parameter.get("ManualRemoval", {}).get("indices", []) or [])

    # helpers
    def _selected_indices_from_checks(n):
        sel = []
        for i in range(n):
            tag = f"manual_remove_single_chk_{i}"
            if dpg.does_item_exist(tag) and dpg.get_value(tag):
                sel.append(i)
        return sel

    def _update_plot():
        n = len(f)
        sel = set(_selected_indices_from_checks(n))

        keep_mask = np.ones(n, dtype=bool)
        if sel:
            keep_mask[list(sel)] = False

        # kept points
        kept_x = Re[keep_mask].tolist()
        kept_y = (-Im[keep_mask]).tolist()

        # removed points
        rem_mask = ~keep_mask
        rem_x = Re[rem_mask].tolist()
        rem_y = (-Im[rem_mask]).tolist()

        # update series data
        if dpg.does_item_exist("manual_cut_single_series_kept"):
            dpg.set_value("manual_cut_single_series_kept", [kept_x, kept_y])
        if dpg.does_item_exist("manual_cut_single_series_removed"):
            dpg.set_value("manual_cut_single_series_removed", [rem_x, rem_y])

    def _on_row_toggle(sender, app_data, user_data):
        # live update when checkbox toggled
        _update_plot()

    def _hover():
        if not dpg.is_item_hovered("manual_cut_single_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()  # plot coordinates

        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        dpg.set_value(
            "manual_cut_single_hover_text",
            f"Hover -> Index: {idx+1} | f: {f[idx]:.3e} Hz | Re: {Re[idx]:.3e} | Im: {Im[idx]:.3e}"
        )
        
    def _toggle_nearest_point():
        if not dpg.is_item_hovered("manual_cut_single_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()
        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        tag = f"manual_remove_single_chk_{idx}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, not dpg.get_value(tag))
            _update_plot()


    # ---- build window (no context managers) ----
    dpg.add_window(
        tag="manual_cut_single_window",
        label="Manual Point Removal: "+ config.display_file,
        modal=True,
        width=1200,
        height=700,
        no_collapse=True,
        no_resize=False
    )

    dpg.add_group(parent="manual_cut_single_window", tag="manual_cut_single_group", horizontal=True)
    dpg.add_child_window(parent="manual_cut_single_group", tag="manual_cut_single_left", width=560, height=-55, border=True)
    dpg.add_child_window(parent="manual_cut_single_group", tag="manual_cut_single_right", width=-1, height=-55, border=True)

    # ---- TABLE ----
    dpg.add_table(
        parent="manual_cut_single_left",
        tag="manual_cut_single_table",
        header_row=True,
        resizable=True,
        scrollX=True,
        scrollY=True,
        borders_innerV=True,
        borders_outerV=True,
        borders_outerH=True,
        policy=dpg.mvTable_SizingFixedFit,
        height=-1
    )

    dpg.add_table_column(parent="manual_cut_single_table", label="Remove", width_fixed=True, init_width_or_weight=70)
    dpg.add_table_column(parent="manual_cut_single_table", label="Index",  width_fixed=True, init_width_or_weight=60)
    dpg.add_table_column(parent="manual_cut_single_table", label="Freq [Hz]", width_fixed=True, init_width_or_weight=150)
    dpg.add_table_column(parent="manual_cut_single_table", label="Re", width_fixed=True, init_width_or_weight=130)
    dpg.add_table_column(parent="manual_cut_single_table", label="Im", width_fixed=True, init_width_or_weight=130)

    for i in range(len(f)):
        row = f"manual_cut_single_row_{i}"
        dpg.add_table_row(parent="manual_cut_single_table", tag=row)

        dpg.add_checkbox(
            parent=row,
            tag=f"manual_remove_single_chk_{i}",
            default_value=(i in prev),
            callback=_on_row_toggle
        )

        dpg.add_text(parent=row, default_value=str(i + 1))
        dpg.add_text(parent=row, default_value=f"{float(f[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Re[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Im[i]):.6e}")

    # ---- PLOT ----
    dpg.add_plot(parent="manual_cut_single_right", tag="manual_cut_single_plot", width=-1, height=-1, no_menus=False, equal_aspects = True)
    dpg.add_plot_axis(dpg.mvXAxis, parent="manual_cut_single_plot", tag="manual_cut_single_x", label="Z' [Ohm·cm2]")
    dpg.add_plot_axis(dpg.mvYAxis, parent="manual_cut_single_plot", tag="manual_cut_single_y", label="-Z'' [Ohm·cm2]")

    # We create two scatter series and then update them live
    dpg.add_scatter_series([], [], parent="manual_cut_single_y", tag="manual_cut_single_series_kept", label="Kept")
    dpg.add_scatter_series([], [], parent="manual_cut_single_y", tag="manual_cut_single_series_removed", label="Removed")
    dpg.add_plot_legend(parent="manual_cut_single_plot")

    dpg.add_text(parent="manual_cut_single_right", default_value="Hover -> Index: -", tag="manual_cut_single_hover_text")

    # handler for hover
    if dpg.does_item_exist("manual_cut_single_handlers"):
        dpg.delete_item("manual_cut_single_handlers")
    dpg.add_handler_registry(tag="manual_cut_single_handlers")
    dpg.add_mouse_move_handler(parent="manual_cut_single_handlers", callback=lambda s, a: _hover())

    dpg.add_mouse_click_handler(
        parent="manual_cut_single_handlers",
        button=dpg.mvMouseButton_Left,
        callback=lambda s, a: _toggle_nearest_point()
    )

    # initial plot update (reflect prev selection)
    _update_plot()

    # ---- Buttons ----
    dpg.add_separator(parent="manual_cut_single_window")
    dpg.add_group(parent="manual_cut_single_window", tag="manual_cut_single_buttons", horizontal=True)

    dpg.add_button(
        parent="manual_cut_single_buttons",
        label="Process manually-cut data",
        callback=lambda: process_manually_cut_data(config, len(f))
    )
    dpg.add_button(
        parent="manual_cut_single_buttons",
        label="Cancel",
        callback=lambda: close_manual_cut_window()
    )

def close_manual_cut_window():
    if dpg.does_item_exist("manual_cut_single_handlers"):
        dpg.delete_item("manual_cut_single_handlers")
    if dpg.does_item_exist("manual_cut_single_window"):
        dpg.delete_item("manual_cut_single_window")

def process_manually_cut_data(config, n_points_preview):
    EIS_new = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=12.56, n_cell=1, file_folder=config.folder_path, filename=None)
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    gui_utils.eis_functions.load_parameters(None, None, config, EIS_new)

    indices = []
    for i in range(n_points_preview):
        if dpg.does_item_exist(f"manual_remove_single_chk_{i}") and dpg.get_value(f"manual_remove_single_chk_{i}"):
            indices.append(i)  # 0-based relative to the preview array

    close_manual_cut_window()
    n = len(EIS_tmp.truncated["f"])
    if indices:
        mask = np.ones(n, dtype=bool)
        mask[indices] = False
        for key in EIS_tmp.truncated.keys():
            if EIS_tmp.truncated[key] is not None:
                EIS_tmp.truncated[key] = np.asarray(EIS_tmp.truncated[key])[mask]

    # 05 - KK test
    if EIS_tmp.parameter['KK']['KK_test']:
        EIS_tmp.KK_test(EIS_tmp.truncated)
    
    # 06 - Data cut based on KK residual
    if EIS_tmp.parameter['KK']['RmNonKK']:
        EIS_tmp.rm_auto_KK()
        EIS_tmp.KK_test(EIS_tmp.truncated)
    
    # 06 - Get smoothed data, LCcorrected data, and extrapolated data
    EIS_tmp.parameter['Smoothing']['fmax'] = max(EIS_tmp.truncated['f'])
    EIS_tmp.parameter['Smoothing']['fmin'] = min(EIS_tmp.truncated['f'])
    EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
    EIS_tmp.store['RsLCinv_kk']['L'] = 0
    EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0
    EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
    EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

    # Update figures and tables
    gui_utils.eis_table.table_update(config)
    gui_utils.eis_plots.update_single_plots(config)
    gui_utils.eis_plots.update_all_plots(config)