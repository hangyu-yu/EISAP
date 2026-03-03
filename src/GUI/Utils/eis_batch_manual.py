import os
import copy
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
from src.Methods.DRT.DRT import DRT

def reset_batch_cut(config):
    try:
        for file_name in config.selected_files:
            file_name_no_ext = os.path.splitext(file_name)[0]
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Store internally
            EIS_tmp.parameter["ManualRemoval"] = {"enabled": True, "indices": ""}
    except Exception as e:
        print(f"[Error] Failed to reset manual cut for {file_name_no_ext}: {e}")
    dpg.set_value("input_manual_remove_batch_indices", EIS_tmp.parameter["ManualRemoval"]["indices"])

def compress_indices(indices_1based):
    if not indices_1based:
        return ""
    indices = sorted(set(indices_1based))
    ranges = []
    start = prev = indices[0]
    for x in indices[1:]:
        if x == prev + 1:
            prev = x
        else:
            ranges.append(str(start) if start == prev else f"{start}-{prev}")
            start = prev = x
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)

def _get_manualcut_preview_data(config):
    """
    Preview for selector = RAW after ONLY upper/lower cut.
    No significance/outlier/KK/manual removal are applied here.

    This keeps selector indices stable and avoids misleading visuals.
    """
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    f = np.asarray(EIS_tmp.raw["f"], dtype=float)
    Re = np.asarray(EIS_tmp.raw["Re"], dtype=float)
    Im = np.asarray(EIS_tmp.raw["Im"], dtype=float)

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
    if dpg.does_item_exist("manual_cut_batch_window"):
        close_manual_cut_window()

    # preview arrays
    f, Re, Im = _get_manualcut_preview_data(config)
    if f is None or len(f) == 0:
        return

    Re = np.asarray(Re, dtype=float)
    Im = np.asarray(Im, dtype=float)
    f = np.asarray(f, dtype=float)

    # selection source of truth = current text field (if enabled), otherwise stored parameter
    enabled = dpg.get_value("checkbox_manual_remove_batch_points") if dpg.does_item_exist("checkbox_manual_remove_batch_points") else False
    text = dpg.get_value("input_manual_remove_batch_indices") if dpg.does_item_exist("input_manual_remove_batch_indices") else ""

    if enabled and text.strip():
        prev = set(parse_indices_1based_to_0based(text))
    else:
        prev = set(config.store[file_key]["EIS"].parameter.get("ManualRemoval", {}).get("indices", []) or [])

    # helpers
    def _selected_indices_from_checks(n):
        sel = []
        for i in range(n):
            tag = f"manual_remove_batch_chk_{i}"
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
        if dpg.does_item_exist("manual_cut_batch_series_kept"):
            dpg.set_value("manual_cut_batch_series_kept", [kept_x, kept_y])
        if dpg.does_item_exist("manual_cut_batch_series_removed"):
            dpg.set_value("manual_cut_batch_series_removed", [rem_x, rem_y])

    def _on_row_toggle(sender, app_data, user_data):
        # live update when checkbox toggled
        _update_plot()

    def _hover():
        if not dpg.is_item_hovered("manual_cut_batch_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()  # plot coordinates

        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        dpg.set_value(
            "manual_cut_batch_hover_text",
            f"Hover -> Index: {idx+1} | f: {f[idx]:.3e} Hz | Re: {Re[idx]:.3e} | Im: {Im[idx]:.3e}"
        )
        
    def _toggle_nearest_point():
        if not dpg.is_item_hovered("manual_cut_batch_plot"):
            return

        mx, my = dpg.get_plot_mouse_pos()
        y_plot = -Im
        dist = (Re - mx) ** 2 + (y_plot - my) ** 2
        idx = int(np.argmin(dist))

        tag = f"manual_remove_batch_chk_{idx}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, not dpg.get_value(tag))
            _update_plot()

    # ---- build window (no context managers) ----
    dpg.add_window(
        tag="manual_cut_batch_window",
        label="Manual Point Removal",
        modal=True,
        width=1200,
        height=700,
        no_collapse=True,
        no_resize=False
    )

    dpg.add_group(parent="manual_cut_batch_window", tag="manual_cut_batch_group", horizontal=True)
    dpg.add_child_window(parent="manual_cut_batch_group", tag="manual_cut_batch_left", width=560, height=-55, border=True)
    dpg.add_child_window(parent="manual_cut_batch_group", tag="manual_cut_batch_right", width=-1, height=-55, border=True)

    # ---- TABLE ----
    dpg.add_table(
        parent="manual_cut_batch_left",
        tag="manual_cut_batch_table",
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

    dpg.add_table_column(parent="manual_cut_batch_table", label="Remove", width_fixed=True, init_width_or_weight=70)
    dpg.add_table_column(parent="manual_cut_batch_table", label="Index",  width_fixed=True, init_width_or_weight=60)
    dpg.add_table_column(parent="manual_cut_batch_table", label="Freq [Hz]", width_fixed=True, init_width_or_weight=150)
    dpg.add_table_column(parent="manual_cut_batch_table", label="Re", width_fixed=True, init_width_or_weight=130)
    dpg.add_table_column(parent="manual_cut_batch_table", label="Im", width_fixed=True, init_width_or_weight=130)

    for i in range(len(f)):
        row = f"manual_cut_batch_row_{i}"
        dpg.add_table_row(parent="manual_cut_batch_table", tag=row)

        dpg.add_checkbox(
            parent=row,
            tag=f"manual_remove_batch_chk_{i}",
            default_value=(i in prev),
            callback=_on_row_toggle
        )

        dpg.add_text(parent=row, default_value=str(i + 1))
        dpg.add_text(parent=row, default_value=f"{float(f[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Re[i]):.6e}")
        dpg.add_text(parent=row, default_value=f"{float(Im[i]):.6e}")

    # ---- PLOT ----
    dpg.add_plot(parent="manual_cut_batch_right", tag="manual_cut_batch_plot", width=-1, height=-1, no_menus=False)
    dpg.add_plot_axis(dpg.mvXAxis, parent="manual_cut_batch_plot", tag="manual_cut_batch_x", label="Z' [Ohm·cm2]")
    dpg.add_plot_axis(dpg.mvYAxis, parent="manual_cut_batch_plot", tag="manual_cut_batch_y", label="-Z'' [Ohm·cm2]")

    # We create two scatter series and then update them live
    dpg.add_scatter_series([], [], parent="manual_cut_batch_y", tag="manual_cut_batch_series_kept", label="Kept")
    dpg.add_scatter_series([], [], parent="manual_cut_batch_y", tag="manual_cut_batch_series_removed", label="Removed")
    dpg.add_plot_legend(parent="manual_cut_batch_plot")

    dpg.add_text(parent="manual_cut_batch_right", default_value="Hover -> Index: -", tag="manual_cut_batch_hover_text")

    # handler for hover
    if dpg.does_item_exist("manual_cut_batch_handlers"):
        dpg.delete_item("manual_cut_batch_handlers")
    dpg.add_handler_registry(tag="manual_cut_batch_handlers")
    dpg.add_mouse_move_handler(parent="manual_cut_batch_handlers", callback=lambda s, a: _hover())

    dpg.add_mouse_click_handler(
        parent="manual_cut_batch_handlers",
        button=dpg.mvMouseButton_Left,
        callback=lambda s, a: _toggle_nearest_point()
    )

    # initial plot update (reflect prev selection)
    _update_plot()

    # ---- Buttons ----
    dpg.add_separator(parent="manual_cut_batch_window")
    dpg.add_group(parent="manual_cut_batch_window", tag="manual_cut_batch_buttons", horizontal=True)

    dpg.add_button(
        parent="manual_cut_batch_buttons",
        label="Process manually-cut data",
        callback=lambda: process_manually_cut_data(config, len(f))
    )
    dpg.add_button(
        parent="manual_cut_batch_buttons",
        label="Cancel",
        callback=lambda: close_manual_cut_window()
    )

def close_manual_cut_window():
    if dpg.does_item_exist("manual_cut_batch_handlers"):
        dpg.delete_item("manual_cut_batch_handlers")
    if dpg.does_item_exist("manual_cut_batch_window"):
        dpg.delete_item("manual_cut_batch_window")

def process_manually_cut_data(config, n_points_preview):
    EIS = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=12.56, n_cell=1, file_folder=config.folder_path, filename=None)
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]

    selected0 = []
    for i in range(n_points_preview):
        if dpg.does_item_exist(f"manual_remove_batch_chk_{i}") and dpg.get_value(f"manual_remove_batch_chk_{i}"):
            selected0.append(i)  # 0-based relative to the preview array

    # Write back to the text input as 1-based compact ranges
    selected1 = [i + 1 for i in selected0]
    dpg.set_value("input_manual_remove_batch_indices", compress_indices(selected1))
    dpg.set_value("checkbox_manual_remove_batch_points", True)
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]

        if file_name_no_ext not in config.store.keys():
            # If the file isn't loaded yet, nothing meaningful to process here
            # (data_import should create the store entry + raw data).
            config.store[file_name_no_ext] = {}
            config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)

        EIS_tmp = config.store[file_name_no_ext]['EIS']

        # Store internally
        EIS_tmp.parameter["ManualRemoval"] = {"enabled": True, "indices": selected0}

        # ---------------------------------------------------------------------
        # 0) Always start from RAW (do NOT touch raw; rebuild truncated fresh)
        # ---------------------------------------------------------------------
        if EIS_tmp.raw is None or EIS_tmp.raw.get("f", None) is None:
            print(f"[Warning] No raw data found for {file_name_no_ext}. Skipping.")
            continue

        EIS_tmp.truncated = {
            "f": np.copy(EIS_tmp.raw["f"]),
            "Re": np.copy(EIS_tmp.raw["Re"]),
            "Im": np.copy(EIS_tmp.raw["Im"]),
            "Z": np.copy(EIS_tmp.raw["Z"]),
        }
        # carry significance if present (some routines may expect it)
        if "significance" in EIS_tmp.raw and EIS_tmp.raw["significance"] is not None:
            EIS_tmp.truncated["significance"] = np.copy(EIS_tmp.raw["significance"])

        # ---------------------------------------------------------------------
        # 2) Manual removal (ONLY on truncated, AFTER auto cuts, BEFORE smoothing)
        # ---------------------------------------------------------------------
        mr = EIS_tmp.parameter.get("ManualRemoval", {"enabled": False, "indices": []})
        if mr.get("enabled", False) and EIS_tmp.raw is not None and EIS_tmp.raw.get("f", None) is not None:
            indices = mr.get("indices", [])
            n = len(EIS_tmp.raw["f"])

            # Keep valid indices only
            indices = [i for i in indices if 0 <= i < n]

            if indices:
                mask = np.ones(n, dtype=bool)
                mask[indices] = False

                for key in ["f", "Re", "Im", "Z", "significance"]:
                    if key in EIS_tmp.raw and EIS_tmp.raw[key] is not None:
                        EIS_tmp.truncated[key] = np.asarray(EIS_tmp.raw[key])[mask]

                print(f"---- Manual removal applied to truncated ({len(indices)} points) for {file_name_no_ext}.")
        # Recompute KK residuals after manual removal so KK_data matches the final truncated set
        if EIS_tmp.parameter.get('KK', {}).get('KK_test', False):
            EIS_tmp.KK_test(EIS_tmp.truncated)
        # ---------------------------------------------------------------------
        # 3) Derived datasets from (manually) truncated
        # ---------------------------------------------------------------------
        if EIS_tmp.truncated.get("f", None) is None or len(EIS_tmp.truncated["f"]) == 0:
            print(f"[Warning] Truncated data empty after preprocessing for {file_name_no_ext}. Skipping resampling.")
            continue

        EIS_tmp.parameter['Smoothing']['fmax'] = float(np.max(EIS_tmp.truncated['f']))
        EIS_tmp.parameter['Smoothing']['fmin'] = float(np.min(EIS_tmp.truncated['f']))

        EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])

        # reset LC correction state before generating LCcorrect curve
        if 'RsLCinv_kk' in EIS_tmp.store:
            EIS_tmp.store['RsLCinv_kk']['L'] = 0
            EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0

        EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
        EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

        print(f"---- Data has been processed successfully for {file_name_no_ext}.")
    close_manual_cut_window()
    # Update figures and tables
    gui_utils.eis_table.table_update(config)
    gui_utils.eis_plots.update_single_plots(config)
    gui_utils.eis_plots.update_all_plots(config)
