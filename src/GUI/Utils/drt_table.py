import os
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utilis


def table_update(config):
    """Update DRT data tables based on currently selected method (Tikhonov or RBF)."""
    with dpg.theme() as table_theme:
        with dpg.theme_component(dpg.mvTable):
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 5, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Header, (70, 70, 70))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (100, 100, 100))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (50, 50, 50))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))

        with dpg.theme_component(dpg.mvTableRow):
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (40, 40, 40))
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, (60, 60, 60))
        
        with dpg.theme_component(dpg.mvTable):
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)

    if config.store.get("verbose_logs", False):
        print("-- DRT data table updating...")

    if not dpg.does_item_exist("tab_bar_drt_data"):
        print("---- Skip table update: tab_bar_drt_data does not exist.")
        return

    def _ensure_or_clear_tab(tab_tag, tab_label, parent_tag):
        if dpg.does_item_exist(tab_tag):
            dpg.configure_item(tab_tag, label=tab_label)
            dpg.delete_item(tab_tag, children_only=True)
        else:
            dpg.add_tab(label=tab_label, tag=tab_tag, parent=parent_tag)

    def _ensure_or_clear_tab_bar(tab_bar_tag, parent_tag):
        if dpg.does_item_exist(tab_bar_tag):
            dpg.delete_item(tab_bar_tag, children_only=True)
        else:
            dpg.add_tab_bar(tag=tab_bar_tag, parent=parent_tag)

    def _is_valid_result(result):
        return (
            isinstance(result, dict)
            and isinstance(result.get("Re", None), dict)
            and isinstance(result.get("Im", None), dict)
            and isinstance(result.get("ReIm", None), dict)
        )

    def _pick_use_rbf(display_eis):
        if dpg.does_item_exist("radio_drt_method"):
            return dpg.get_value("radio_drt_method") == "RBF-DRT"
        if display_eis is None:
            return False
        return bool(getattr(display_eis, "parameter", {}).get("DRT_RBF", {}).get("enabled", False))

    def _get_result(eis_obj, data_type, use_rbf):
        if eis_obj is None:
            return None
        data_type_map = {
            "truncated": "truncated",
            "smooth": "smooth",
            "LCcorrect": "LCcorrect",
            "extrapolation": "extrapolation",
            "zhit": "zhit",
        }
        suffix = data_type_map.get(data_type)
        if suffix is None:
            return None
        attr_name = f"rbf_{suffix}" if use_rbf else f"tknv_{suffix}"
        return getattr(eis_obj, attr_name, None)

    def _format_value(value, digits=6):
        if value is None:
            return "N/A"
        try:
            return f"{float(value):.{digits}f}"
        except Exception:
            return "N/A"

    def _gamma_axis(category_result):
        g_arr = np.asarray(category_result.get("g", []), dtype=float).reshape(-1)
        f_gamma = category_result.get("f_gamma", None)
        if f_gamma is not None:
            f_gamma_arr = np.asarray(f_gamma, dtype=float).reshape(-1)
            if len(f_gamma_arr) == len(g_arr) and len(g_arr) > 0:
                return f_gamma_arr
        return np.asarray(category_result.get("f", []), dtype=float).reshape(-1)

    display_key = os.path.splitext(config.display_file)[0] if config.display_file not in ([], None) else None
    display_eis = config.store.get(display_key, {}).get("EIS", None) if display_key is not None else None
    use_rbf = _pick_use_rbf(display_eis)
    method_name = "RBF-DRT" if use_rbf else "Tikhonov"

    # Keep tabs persistent and only refresh their contents.
    data_types = ["truncated", "smooth", "LCcorrect", "extrapolation", "zhit", "Resistance_truncated"]

    for data_type in data_types:
        tab_label = "ZHIT" if data_type == "zhit" else data_type[0].upper() + data_type[1:]
        tab_tag = f"tab_drt_{data_type}_data"
        _ensure_or_clear_tab(tab_tag, tab_label, "tab_bar_drt_data")

        if data_type == "Resistance_truncated":
            with dpg.table(
                parent=tab_tag,
                tag=f"tab_drt_{data_type}_data_table",
                header_row=True,
                borders_innerV=True,
                borders_outerV=True,
                borders_outerH=True,
                row_background=True,
                reorderable=True,
                freeze_rows=1,
                scrollX=True,
                scrollY=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                dpg.add_table_column(label="File name", width_fixed=True)
                dpg.add_table_column(label="L-ReIm [H·cm2]", width_stretch=True)
                dpg.add_table_column(label="Rohm-ReIm [Ohm·cm2]", width_stretch=True)
                dpg.add_table_column(label="Rpol-ReIm [Ohm·cm2]", width_stretch=True)

                if config.selected_files:
                    for file_name in config.selected_files:
                        file_name_no_ext = os.path.splitext(file_name)[0]
                        eis_obj = config.store.get(file_name_no_ext, {}).get("EIS", None)
                        result = _get_result(eis_obj, "truncated", use_rbf)
                        rl = result.get("RL", {}) if _is_valid_result(result) else {}
                        with dpg.table_row():
                            dpg.add_text(gui_utilis.small_functions.string_abbreviation(file_name_no_ext, 12, 12))
                            dpg.add_text(_format_value(rl.get("L_ReIm", None)))
                            dpg.add_text(_format_value(rl.get("Rs_ReIm", None)))
                            dpg.add_text(_format_value(rl.get("Rp_ReIm", None)))
            dpg.bind_item_theme(f"tab_drt_{data_type}_data_table", table_theme)
            continue

        sub_tab_bar_tag = f"tab_bar_drt_{data_type}_data"
        _ensure_or_clear_tab_bar(sub_tab_bar_tag, tab_tag)
        current_result = _get_result(display_eis, data_type, use_rbf)

        for data_category in ["ReIm", "Re", "Im"]:
            sub_tab_tag = f"tab_drt_{data_type}_{data_category}_data"
            _ensure_or_clear_tab(sub_tab_tag, f"{tab_label}_{data_category}", sub_tab_bar_tag)

            if not _is_valid_result(current_result) or data_category not in current_result:
                dpg.add_text(f"No {method_name} data for {data_type}_{data_category}.", parent=sub_tab_tag)
                continue

            cat = current_result[data_category]
            f_arr = _gamma_axis(cat)
            g_arr = np.asarray(cat.get("g", []), dtype=float).reshape(-1)
            re_arr = np.asarray(cat.get("Re", []), dtype=float).reshape(-1)
            im_arr = np.asarray(cat.get("Im", []), dtype=float).reshape(-1)
            n = min(len(f_arr), len(g_arr), len(re_arr), len(im_arr))

            with dpg.table(
                parent=sub_tab_tag,
                tag=f"tab_drt_{data_type}_{data_category}_data_table",
                header_row=True,
                borders_innerV=True,
                borders_outerV=True,
                borders_outerH=True,
                row_background=True,
                reorderable=True,
                freeze_rows=1,
                scrollX=True,
                scrollY=True,
                policy=dpg.mvTable_SizingFixedFit,
            ):
                dpg.add_table_column(label="ID", width_fixed=True)
                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                dpg.add_table_column(label="g [Ohm·s·cm2]", width_stretch=True)
                dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)

                for idx in range(n):
                    with dpg.table_row():
                        dpg.add_text(f"{idx + 1}")
                        dpg.add_text(_format_value(f_arr[idx], digits=2))
                        dpg.add_text(_format_value(g_arr[idx], digits=6))
                        dpg.add_text(_format_value(re_arr[idx], digits=6))
                        dpg.add_text(_format_value(im_arr[idx], digits=6))

            dpg.bind_item_theme(f"tab_drt_{data_type}_{data_category}_data_table", table_theme)

    if config.store.get("verbose_logs", False):
        if config.display_file not in ([], None):
            print(f"---- DRT data table updated successfully using {method_name} data.")
        else:
            print("---- Continue. No display file selected for DRT table.")