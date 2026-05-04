import os
import copy
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
import src.GUI.Utils.progress_modal as progress_modal
from src.Methods.DRT.DRT import DRT


def reset_batch_cut(config):
    try:
        for file_name in config.selected_files:
            file_name_no_ext = os.path.splitext(file_name)[0]
            EIS_tmp = config.store[file_name_no_ext]['EIS']
            # Store internally
            EIS_tmp.parameter["ManualRemoval"] = {"enable": True, "indices": []}
    except Exception as e:
        print(f"[Error] Failed to reset manual cut for {file_name_no_ext}: {e}")
    dpg.set_value("input_manual_remove_batch_indices", "")

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

    # Pre-flight: check ALL selected files have raw data imported.
    # Run BEFORE the store guard so unimported files also trigger the dialog.
    missing_data_files = []
    for _sel_file in (config.selected_files or []):
        _fk = os.path.splitext(_sel_file)[0]
        _raw_f = None
        if _fk in config.store and "EIS" in config.store[_fk]:
            _raw_f = config.store[_fk]["EIS"].raw["f"]
        if _raw_f is None or (hasattr(_raw_f, "__len__") and len(_raw_f) == 0):
            missing_data_files.append(_sel_file)
    if missing_data_files:
        progress_modal.show_error_dialog(
            "Manual Removal \u2014 Missing Data",
            "The following files have not been imported yet.\n"
            "Please click 'Data Import' for these files first:\n\n"
            + "\n".join(f"  \u2022 {f}" for f in missing_data_files),
        )
        return

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

    # selection source of truth = current text field (if enable), otherwise stored parameter
    removal_enable = dpg.get_value("checkbox_manual_remove_batch_points") if dpg.does_item_exist("checkbox_manual_remove_batch_points") else False
    removal_text = dpg.get_value("input_manual_remove_batch_indices") if dpg.does_item_exist("input_manual_remove_batch_indices") else ""

    if removal_enable and removal_text.strip():
        prev = set(parse_indices_1based_to_0based(removal_text))
    else:
        prev_raw = config.store[file_key]["EIS"].parameter.get("ManualRemoval", {}).get("indices", [])
        if isinstance(prev_raw, str):
            prev = set(parse_indices_1based_to_0based(prev_raw))
        else:
            prev = set()
            for _v in (prev_raw or []):
                try:
                    prev.add(int(_v))
                except Exception:
                    continue

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
    dpg.add_plot(parent="manual_cut_batch_right", tag="manual_cut_batch_plot", width=-1, height=-1, no_menus=False, equal_aspects=True)
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

    # Fit both axes once after initial data is loaded, then leave them free to pan/zoom.
    dpg.fit_axis_data("manual_cut_batch_x")
    dpg.fit_axis_data("manual_cut_batch_y")

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
    """Collect selected indices and apply manual removal to all selected files."""
    EIS_new = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=12.56, n_cell=1, file_folder=config.folder_path, filename=None)
    file_key = os.path.splitext(config.display_file)[0]
    EIS_tmp = config.store[file_key]["EIS"]
    gui_utils.eis_functions.load_parameters(None, None, config, EIS_new)

    # Collect selected indices (0-based)
    selected_indices = []
    for i in range(n_points_preview):
        if dpg.does_item_exist(f"manual_remove_batch_chk_{i}") and dpg.get_value(f"manual_remove_batch_chk_{i}"):
            selected_indices.append(i)

    # Write back to the text input as 1-based compact ranges
    selected_indices = sorted(set(selected_indices))
    selected1 = [i + 1 for i in selected_indices]
    dpg.set_value("input_manual_remove_batch_indices", compress_indices(selected1))
    dpg.set_value("checkbox_manual_remove_batch_points", True)
    close_manual_cut_window()
    dpg.split_frame()

    # Prepare files dictionary for batch processing
    files_dict = {}
    for file_name in config.selected_files:
        file_name_no_ext = os.path.splitext(file_name)[0]
        if file_name_no_ext not in config.store.keys():
            config.store[file_name_no_ext] = {}
            config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS_new)
        
        # Store internal parameter
        EIS_tmp_file = config.store[file_name_no_ext]['EIS']
        EIS_tmp_file.parameter["ManualRemoval"] = {"enable": True, "indices": list(selected_indices)}
        files_dict[file_name_no_ext] = selected_indices

    # Open progress and apply manual removal
    progress = progress_modal.open_progress(
        "EIS - Batch Manual Removal",
        "Applying manual removal to selected files...",
        len(config.selected_files),
        window_tag="batch_manual_remove_progress",
    )
    
    try:
        # Call unified processing function (with batch=True for progress tracking)
        gui_utils.eis_single_manual.apply_manual_removal(config, files_dict, progress, is_batch=True)
    except Exception as exc:
        import traceback
        print(f"[Error] Batch manual removal:\n{traceback.format_exc()}")
        progress_modal.show_error_dialog(
            "EIS - Batch Manual Removal Error",
            f"{type(exc).__name__}: {exc}",
            file_hint="",
        )
    finally:
        progress_modal.close_progress(progress)

    # Update figures and tables
    gui_utils.eis_table.table_update(config)
    gui_utils.eis_plots.update_single_plots(config)
    gui_utils.eis_plots.update_all_plots(config)
