import os
import math
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def table_update(config):
    """
    Update the EIS data tables. Tabs are preserved across refreshes (children-only clear)
    to avoid active-tab jumping and maintain stable tab order.
    Resistances tab is always last.
    """
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
        print("-- EIS data table updating...")

    if not dpg.does_item_exist("tab_bar_eis_data"):
        return

    def _ensure_or_clear_tab(tab_tag, tab_label, parent_tag):
        """Keep tab alive and clear its children to avoid ordering jumps."""
        if dpg.does_item_exist(tab_tag):
            dpg.delete_item(tab_tag, children_only=True)
        else:
            dpg.add_tab(label=tab_label, tag=tab_tag, parent=parent_tag)

    display_key = os.path.splitext(config.display_file)[0] if config.display_file not in ([], None) else None
    has_eis = (
        display_key is not None
        and display_key in config.store
        and 'EIS' in config.store[display_key]
    )
    has_kk_data = has_eis and config.store[display_key]['EIS'].KK_data['f'] is not None

    # ── Data tabs (always before Resistances) ────────────────────────────────
    for data_category in ["KK_data", "raw", "truncated", "LCcorrect", "smooth", "extrapolation"]:
        tab_tag   = f"tab_eis_{data_category}_data"
        table_tag = f"tab_eis_{data_category}_data_table"
        _ensure_or_clear_tab(tab_tag, data_category, "tab_bar_eis_data")

        if not has_eis:
            continue

        with dpg.table(
            parent=tab_tag,
            tag=table_tag,
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
            if data_category != "KK_data":
                dpg.add_table_column(label="ID", width_fixed=True)
                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                dpg.add_table_column(label="Re [Ohm·cm2]", width_stretch=True)
                dpg.add_table_column(label="Im [Ohm·cm2]", width_stretch=True)
                dpg.add_table_column(label="Z [Ohm·cm2]", width_stretch=True)
                dpg.add_table_column(label="Phase [deg]", width_stretch=True)
                if has_kk_data:
                    data = config.store[display_key]['EIS'][data_category]
                    for row_idx in range(len(data['f'])):
                        with dpg.table_row():
                            phase = math.degrees(math.atan2(data['Im'][row_idx], data['Re'][row_idx]))
                            dpg.add_text(f"{row_idx + 1}")
                            dpg.add_text(f"{data['f'][row_idx]:.2f}")
                            dpg.add_text(f"{data['Re'][row_idx]:.6f}")
                            dpg.add_text(f"{data['Im'][row_idx]:.6f}")
                            dpg.add_text(f"{data['Z'][row_idx]:.4f}")
                            dpg.add_text(f"{phase:.2f}")
            else:
                dpg.add_table_column(label="ID", width_fixed=True)
                dpg.add_table_column(label="Frequency [Hz]", width_stretch=True)
                dpg.add_table_column(label="Re residual [%]", width_stretch=True)
                dpg.add_table_column(label="Im residual [%]", width_stretch=True)
                if has_kk_data:
                    data = config.store[display_key]['EIS'].KK_data
                    for row_idx in range(len(data['f'])):
                        with dpg.table_row():
                            dpg.add_text(f"{row_idx + 1}")
                            dpg.add_text(f"{data['f'][row_idx]:.2f}")
                            dpg.add_text(f"{data['delta_Re_kk'][row_idx]:.6f}")
                            dpg.add_text(f"{data['delta_Im_kk'][row_idx]:.6f}")
        dpg.bind_item_theme(table_tag, table_theme)

    # ── Resistances tab — always last ─────────────────────────────────────────
    _ensure_or_clear_tab("tab_eis_Resistances_data", "Resistances", "tab_bar_eis_data")
    with dpg.table(
        parent="tab_eis_Resistances_data",
        tag="tab_eis_Resistances_data_table",
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
        dpg.add_table_column(label="L [H·cm2]", width_stretch=True)
        dpg.add_table_column(label="C [F/cm2]", width_stretch=True)
        dpg.add_table_column(label="Rohm [Ohm·cm2]", width_stretch=True)
        dpg.add_table_column(label="Rpol [Ohm·cm2]", width_stretch=True)
        if has_eis:
            for file_name in config.selected_files:
                file_name_no_ext = os.path.splitext(file_name)[0]
                if file_name_no_ext in config.store and 'EIS' in config.store[file_name_no_ext]:
                    EIS_tmp = config.store[file_name_no_ext]['EIS']
                    with dpg.table_row():
                        dpg.add_text(gui_utils.small_functions.string_abbreviation(file_name_no_ext, 12, 12))
                        dpg.add_text(f"{float(EIS_tmp.KK_data['L_kk'].item()):.6f}" if EIS_tmp.KK_data['L_kk'] is not None else "N/A")
                        dpg.add_text(f"{float(EIS_tmp.KK_data['C_kk'].item()):.6f}" if EIS_tmp.KK_data['C_kk'] is not None else "N/A")
                        dpg.add_text(f"{float(EIS_tmp.KK_data['res_ohm_kk'].item()):.6f}" if EIS_tmp.KK_data['res_ohm_kk'] is not None else "N/A")
                        dpg.add_text(f"{float(EIS_tmp.KK_data['res_pol_kk'].item()):.6f}" if EIS_tmp.KK_data['res_pol_kk'] is not None else "N/A")
    dpg.bind_item_theme("tab_eis_Resistances_data_table", table_theme)