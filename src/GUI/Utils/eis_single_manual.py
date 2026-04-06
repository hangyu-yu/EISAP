import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
import src.GUI.Utils.progress_modal as progress_modal
from src.Methods.DRT.DRT import DRT

def _get_manualcut_preview_data(config):
    """
    Preview for selector = RAW data only.
    No significance/outlier/KK/manual removal are applied here.

    This keeps indices stable and matches batch manual-removal behavior.
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

    # Pre-flight: check the displayed file has raw data imported.
    # Run BEFORE the store guard so unimported files also trigger the dialog.
    _raw_f = None
    if file_key in config.store and "EIS" in config.store[file_key]:
        _raw_f = config.store[file_key]["EIS"].raw["f"]
    if _raw_f is None or (hasattr(_raw_f, "__len__") and len(_raw_f) == 0):
        progress_modal.show_error_dialog(
            "Manual Removal \u2014 Missing Data",
            f"'{config.display_file}' has not been imported yet.\n"
            "Please click 'Data Import' to import the raw data first.",
        )
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

    # Fit both axes once after initial data is loaded, then leave them free to pan/zoom.
    dpg.fit_axis_data("manual_cut_single_x")
    dpg.fit_axis_data("manual_cut_single_y")

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


def apply_manual_removal(config, files_dict, progress=None, is_batch=False):
    """
    Unified data processing for manual removal (shared by single and batch).
    
    Parameters
    ----------
    config : Configuration object with store, display_file, etc.
    files_dict : dict mapping file_name_no_ext -> indices (0-based list)
                 For single mode: {display_file_key: [indices]}
                 For batch mode: {file_1: [indices], file_2: [indices], ...}
    progress : progress_modal context or None
    is_batch : bool, whether this is batch processing (affects progress updates)
    """
    try:
        file_list = list(files_dict.items())
        total_files = len(file_list)
        
        for file_idx, (file_name_no_ext, indices) in enumerate(file_list):
            if progress and is_batch:
                progress_modal.update_progress(progress, file_idx, file_name_no_ext)

            if file_name_no_ext not in config.store or "EIS" not in config.store[file_name_no_ext]:
                print(f"[Warning] EIS data not found for {file_name_no_ext}. Skipping.")
                if progress and is_batch:
                    progress_modal.update_progress(progress, file_idx + 1, file_name_no_ext)
                continue

            EIS_tmp = config.store[file_name_no_ext]["EIS"]

            # -----------------------------------------------------------------
            # 0) Always start from RAW (rebuild truncated fresh from raw)
            # -----------------------------------------------------------------
            if EIS_tmp.raw is None or EIS_tmp.raw.get("f", None) is None:
                print(f"[Warning] No raw data found for {file_name_no_ext}. Skipping.")
                if progress and is_batch:
                    progress_modal.update_progress(progress, file_idx + 1, file_name_no_ext)
                continue

            EIS_tmp.truncated = {
                "f": np.copy(EIS_tmp.raw["f"]),
                "Re": np.copy(EIS_tmp.raw["Re"]),
                "Im": np.copy(EIS_tmp.raw["Im"]),
                "Z": np.copy(EIS_tmp.raw["Z"]),
            }
            if "significance" in EIS_tmp.raw and EIS_tmp.raw["significance"] is not None:
                EIS_tmp.truncated["significance"] = np.copy(EIS_tmp.raw["significance"])

            # -----------------------------------------------------------------
            # 1) Apply manual removal (filter indices from raw)
            # -----------------------------------------------------------------
            n = len(EIS_tmp.raw["f"])
            indices = [idx for idx in sorted(set(indices)) if 0 <= idx < n]
            
            if indices:
                mask = np.ones(n, dtype=bool)
                mask[indices] = False
                for key in ["f", "Re", "Im", "Z", "significance"]:
                    if key in EIS_tmp.raw and EIS_tmp.raw[key] is not None:
                        EIS_tmp.truncated[key] = np.asarray(EIS_tmp.raw[key])[mask]
                print(f"---- Manual removal applied to truncated ({len(indices)} points) for {file_name_no_ext}.")

            # -----------------------------------------------------------------
            # 2) KK test (if enabled)
            # -----------------------------------------------------------------
            if EIS_tmp.parameter.get('KK', {}).get('KK_test', False):
                EIS_tmp.KK_test(EIS_tmp.truncated)

            if EIS_tmp.parameter.get('KK', {}).get('RmNonKK', False):
                EIS_tmp.rm_auto_KK()
                EIS_tmp.KK_test(EIS_tmp.truncated)

            # -----------------------------------------------------------------
            # 3) Derived datasets (smooth, LCcorrect, extrapolation)
            # -----------------------------------------------------------------
            if EIS_tmp.truncated.get("f", None) is None or len(EIS_tmp.truncated["f"]) == 0:
                print(f"[Warning] Truncated data empty after preprocessing for {file_name_no_ext}. Skipping resampling.")
                if progress and is_batch:
                    progress_modal.update_progress(progress, file_idx + 1, file_name_no_ext)
                continue

            EIS_tmp.parameter['Smoothing']['fmax'] = float(np.max(EIS_tmp.truncated['f']))
            EIS_tmp.parameter['Smoothing']['fmin'] = float(np.min(EIS_tmp.truncated['f']))

            EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])

            if 'RsLCinv_kk' in EIS_tmp.store:
                EIS_tmp.store['RsLCinv_kk']['L'] = 0
                EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0

            EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
            EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

            print(f"---- Data has been processed successfully for {file_name_no_ext}.")
            if progress and is_batch:
                progress_modal.update_progress(progress, file_idx + 1, file_name_no_ext)

    except Exception as exc:
        import traceback
        print(f"[Error] Manual removal processing failed: {exc}\n{traceback.format_exc()}")
        raise


def process_manually_cut_data(config, n_points_preview):
    """Collect selected indices and apply manual removal to current file."""
    progress = progress_modal.open_progress(
        "EIS - Single Manual Removal",
        "Applying manual removal to current file...",
        5,
        window_tag="single_manual_remove_progress",
    )
    try:
        file_key = os.path.splitext(config.display_file)[0]
        EIS_tmp = config.store[file_key]["EIS"]

        # Collect selected indices (0-based)
        indices = []
        for i in range(n_points_preview):
            if dpg.does_item_exist(f"manual_remove_single_chk_{i}") and dpg.get_value(f"manual_remove_single_chk_{i}"):
                indices.append(i)

        # Store parameters for single-point removal (no batch mode enabled)
        EIS_tmp.parameter["ManualRemoval"] = {"enable": False, "indices": sorted(set(indices))}
        EIS_tmp.parameter["ManualRemoval"]["Enable"] = False
        progress_modal.update_progress(progress, 1, "Selection parsed")

        close_manual_cut_window()

        # Call unified processing function
        apply_manual_removal(config, {file_key: indices}, progress)
        progress_modal.update_progress(progress, 3, "Data processed")

        # Update figures and tables
        gui_utils.eis_table.table_update(config)
        gui_utils.eis_plots.update_single_plots(config)
        progress_modal.update_progress(progress, 4, "Single plot updated")
        gui_utils.eis_plots.update_all_plots(config)
        progress_modal.update_progress(progress, 5, "Done")
    except Exception as exc:
        import traceback
        print(f"[Error] Single manual removal failed: {exc}\\n{traceback.format_exc()}")
        progress_modal.show_error_dialog(
            "EIS - Single Manual Removal Error",
            f"{type(exc).__name__}: {exc}",
            file_hint=config.display_file,
        )
    finally:
        progress_modal.close_progress(progress)