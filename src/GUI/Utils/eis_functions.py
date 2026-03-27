import os
import sys
import copy
import numpy as np
import pandas as pd
import importlib.util
import dearpygui.dearpygui as dpg

def _parse_index_list(text: str):
    """
    Parse a user string like '1, 3, 10-15' into a sorted unique list of
    0-based indices.

    User input is 1-based.
    Internal indexing is converted to 0-based.

    Supports:
      - commas
      - spaces
      - ranges like 10-15
    """

    if text is None:
        return []

    s = str(text).strip()
    if s == "" or s.lower() in {"n/a", "na", "none"}:
        return []

    out = []

    for token in s.replace(" ", "").split(","):
        if token == "":
            continue

        # Range handling (e.g., 3-7)
        if "-" in token:
            parts = token.split("-", 1)
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                a, b = int(parts[0]), int(parts[1])
                lo, hi = (a, b) if a <= b else (b, a)

                # Convert to 0-based and ignore <= 0
                out.extend([i - 1 for i in range(lo, hi + 1) if i > 0])

        # Single index
        else:
            if token.isdigit():
                val = int(token)
                if val > 0:
                    out.append(val - 1)

    # Unique + sorted
    return sorted(set(out))

def call_function(file_path, *args, **kwargs):
    """Directly call a function with the same name as the Python file"""
    # Extract the module name (remove path and .py)
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Dynamically load the module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    # Retrieve and call the function with the same name
    func = getattr(module, module_name)
    return func(*args, **kwargs)  # Directly execute and return the result

def data_import(sender, app_data, config, EIS):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "EIS — Data Import", "Importing raw EIS data...",
        max(1, len(config.selected_files)),
    )
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_path = os.path.join(config.folder_path, file_name)

            if file_path is None:
                raise FileNotFoundError('The specified file does not exist.')
            else:
                metadata, data = call_function(config.data_import_function, file_path)
                file_name_no_ext = os.path.splitext(file_name)[0]
                config.store[file_name_no_ext] = {}
                config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
                EIS_tmp = config.store[file_name_no_ext]['EIS']
                EIS_tmp.filename = file_name
            EIS_tmp.raw['Re'] = data['Re/Ohm'].to_numpy()
            EIS_tmp.raw['Im'] = data['Im/Ohm'].to_numpy()
            EIS_tmp.raw['Z'] = EIS_tmp.raw['Re'] + 1j * EIS_tmp.raw['Im']
            EIS_tmp.raw['f'] = data['Frequency/Hz'].to_numpy()
            if 'Significance' in data.columns:
                EIS_tmp.raw['significance'] = data['Significance'].to_numpy()
            EIS_tmp.info = metadata
            if 'cell_area_old' in EIS_tmp.store.keys():
                EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, {'CellArea': EIS_tmp.store['cell_area_old']/EIS_tmp.store["n_cell_old"]})
            elif os.path.exists(os.path.join(config.folder_path, file_name)):
                EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, {'CellArea': EIS_tmp.parameter["Sample"]["CellArea"]/EIS_tmp.parameter["Sample"]["n_cell"]})
            else:
                EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, {'CellArea': 1})

            _pm.update_progress(progress, i + 1, file_name)

        if dpg.does_item_exist("tab_eis_raw_data_table"):
            dpg.configure_item("combo_eis_plot_file", items=config.selected_files)
            config.display_file = config.selected_files[0] if config.selected_files else ""
            dpg.set_value("combo_eis_plot_file", config.display_file)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] EIS data_import:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("EIS — Data Import Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

def load_parameters(sender, app_data, config, EIS):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "EIS — Load Parameters", "Loading EIS parameters...",
        max(1, len(config.selected_files)),
    )
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]
            if file_name_no_ext not in config.store.keys():
                config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)
            else:
                EIS_tmp = config.store[file_name_no_ext]['EIS']
                if 'cell_area_old' in EIS_tmp.store.keys():
                    EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, {'CellArea': EIS_tmp.store["n_cell_old"]/EIS_tmp.store['cell_area_old']})
                elif os.path.exists(os.path.join(config.folder_path, file_name)):
                    EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, {'CellArea': EIS_tmp.parameter["Sample"]["n_cell"]/EIS_tmp.parameter["Sample"]["CellArea"]})
                # Load the parameter for the general settings
                EIS_tmp.parameter["Sample"]["n_cell"] = int(dpg.get_value("n_cell"))
                EIS_tmp.parameter["Sample"]["CellArea"] = float(dpg.get_value("CellArea")) / EIS_tmp.parameter["Sample"]["n_cell"]
                EIS_tmp.raw = EIS_tmp.convert2asr(EIS_tmp.raw, EIS_tmp.parameter['Sample'])
                EIS_tmp.parameter["Sample"]["CellArea"] = float(dpg.get_value("CellArea"))
                EIS_tmp.parameter["Sample"]["instrument_type"] = dpg.get_value("instrument_type")
                EIS_tmp.parameter["Preprocessing"]["num_cut_upper"] = int(dpg.get_value("num_cut_upper"))
                EIS_tmp.parameter["Preprocessing"]["num_cut_lower"] = int(dpg.get_value("num_cut_lower"))
                EIS_tmp.parameter["RM_significance"]["sig_threshold"] = float(dpg.get_value("sig_threshold"))
                EIS_tmp.parameter["RM_significance"]["rm_significance"] = dpg.get_value("rm_significance")
                EIS_tmp.parameter["Rmoutliers"]["Rmoutliers"] = dpg.get_value("rm_outliers")

                # Load the KK parameters
                EIS_tmp.parameter["KK"]["nRCmax"] = int(dpg.get_value("nRCmax"))
                EIS_tmp.parameter["KK"]["nRC"] = int(dpg.get_value("nRC"))
                EIS_tmp.parameter["KK"]["kk_threshold"] = float(dpg.get_value("kk_threshold"))
                EIS_tmp.parameter["KK"]["mu_threshold"] = float(dpg.get_value("mu_threshold"))
                EIS_tmp.parameter["KK"]["KK_test"] = dpg.get_value("KK_test")
                EIS_tmp.parameter["KK"]["KK_type"] = 'Mu_criterion' if dpg.get_value("KK_type") else 'standard'
                EIS_tmp.parameter["KK"]["RmNonKK"] = dpg.get_value("RmNonKK")

                # Load the EIS parameters
                EIS_tmp.parameter["Smoothing"]["PointsPerDecade"] = int(dpg.get_value("Smooth_PointsPerDecade"))
                EIS_tmp.parameter["Extrapolation"]["fmin"] = float(dpg.get_value("extrapolation_fmin"))
                EIS_tmp.parameter["Extrapolation"]["fmax"] = float(dpg.get_value("extrapolation_fmax"))
                EIS_tmp.parameter["Extrapolation"]["PointsPerDecade"] = int(dpg.get_value("Extrapolation_PointsPerDecade"))

                # Load ZHIT parameters
                EIS_tmp.parameter["ZHIT"]["enable"] = dpg.get_value("zhit_enable")
                EIS_tmp.parameter["ZHIT"]["poly_order"] = int(dpg.get_value("zhit_poly_order"))
                EIS_tmp.parameter["ZHIT"]["window_frac"] = float(dpg.get_value("zhit_window_frac"))

                # Store the cell area
                EIS_tmp.store['cell_area_old'] = EIS_tmp.parameter["Sample"]["CellArea"]
                EIS_tmp.store['n_cell_old'] = EIS_tmp.parameter["Sample"]["n_cell"]

                # Manual removal settings
                EIS_tmp.parameter["ManualRemoval"]["enable"] = dpg.get_value("checkbox_manual_remove_batch_points")
                if config.store.get("verbose_logs", False):
                    print(f"---- EIS parameters have been loaded successfully for {file_name_no_ext}.")
            _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] EIS load_parameters:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("EIS — Load Parameters Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

def process_data(sender, app_data, config, EIS):
    import src.GUI.Utils.progress_modal as _pm
    progress = _pm.open_progress(
        "EIS — Process Data", "Processing EIS data...",
        max(1, len(config.selected_files)),
    )
    _current_file = ""
    try:
        for i, file_name in enumerate(config.selected_files):
            _current_file = file_name
            _pm.update_progress(progress, i, file_name)
            file_name_no_ext = os.path.splitext(file_name)[0]

            if file_name_no_ext not in config.store.keys():
                config.store[file_name_no_ext] = {}
                config.store[file_name_no_ext]['EIS'] = copy.deepcopy(EIS)

            EIS_tmp = config.store[file_name_no_ext]['EIS']

            # -----------------------------------------------------------------
            # 0) Always start from RAW (rebuild truncated fresh)
            # -----------------------------------------------------------------
            if EIS_tmp.raw is None or EIS_tmp.raw.get("f", None) is None:
                print(f"[Warning] No raw data found for {file_name_no_ext}. Skipping.")
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
            # 1) Automatic preprocessing
            # -----------------------------------------------------------------
            EIS_tmp.rm_hfc_lfc()

            if EIS_tmp.parameter.get('RM_significance', {}).get('rm_significance', False):
                EIS_tmp.rm_significance()

            if EIS_tmp.parameter.get('KKpreprocess', {}).get('OptimalCut', False):
                EIS_tmp.Linear_KK_opt_mu_cut(EIS_tmp.truncated, EIS_tmp.parameter['KKpreprocess'])

            if EIS_tmp.parameter.get('Rmoutliers', {}).get('Rmoutliers', False):
                EIS_tmp.rm_outliers()

            if EIS_tmp.parameter.get('KK', {}).get('KK_test', False):
                EIS_tmp.KK_test(EIS_tmp.truncated)

            if EIS_tmp.parameter.get('KK', {}).get('RmNonKK', False):
                EIS_tmp.rm_auto_KK()
                EIS_tmp.KK_test(EIS_tmp.truncated)

            # -----------------------------------------------------------------
            # 2) Manual removal
            # -----------------------------------------------------------------
            mr = EIS_tmp.parameter.get("ManualRemoval", {"enabled": False, "indices": []})
            if mr.get("enabled", False) and EIS_tmp.truncated is not None and EIS_tmp.truncated.get("f", None) is not None:
                indices = mr.get("indices", [])
                n = len(EIS_tmp.truncated["f"])
                indices = [idx for idx in indices if 0 <= idx < n]
                if indices:
                    mask = np.ones(n, dtype=bool)
                    mask[indices] = False
                    for key in ["f", "Re", "Im", "Z", "significance"]:
                        if key in EIS_tmp.truncated and EIS_tmp.truncated[key] is not None:
                            EIS_tmp.truncated[key] = np.asarray(EIS_tmp.truncated[key])[mask]

            if EIS_tmp.parameter.get('KK', {}).get('KK_test', False):
                EIS_tmp.KK_test(EIS_tmp.truncated)

            # -----------------------------------------------------------------
            # 3) Derived datasets
            # -----------------------------------------------------------------
            if EIS_tmp.truncated.get("f", None) is None or len(EIS_tmp.truncated["f"]) == 0:
                print(f"[Warning] Truncated data empty after preprocessing for {file_name_no_ext}. Skipping resampling.")
                continue

            EIS_tmp.parameter['Smoothing']['fmax'] = float(np.max(EIS_tmp.truncated['f']))
            EIS_tmp.parameter['Smoothing']['fmin'] = float(np.min(EIS_tmp.truncated['f']))

            EIS_tmp.smooth = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])

            if 'RsLCinv_kk' in EIS_tmp.store:
                EIS_tmp.store['RsLCinv_kk']['L'] = 0
                EIS_tmp.store['RsLCinv_kk']['Cinv'] = 0

            EIS_tmp.LCcorrect = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Smoothing'])
            EIS_tmp.extrapolation = EIS_tmp.ResampleEIS(EIS_tmp.truncated, EIS_tmp.parameter['Extrapolation'])

            # 4) Z-HIT (optional)
            if EIS_tmp.parameter.get('ZHIT', {}).get('enable', False):
                try:
                    EIS_tmp.ZHIT(EIS_tmp.truncated)
                except Exception as e:
                    print(f"[Warning] Z-HIT failed for {file_name_no_ext}: {e}")
                    EIS_tmp.zhit_data = {k: None for k in EIS_tmp.zhit_data.keys()}
            else:
                EIS_tmp.zhit_data = {k: None for k in EIS_tmp.zhit_data.keys()}

            _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] EIS process_data:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("EIS — Process Data Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)

def save_eis(sender, app_data, config, EIS):
    import src.GUI.Utils.progress_modal as _pm
    n = len(config.selected_files) if config.selected_files else 0
    progress = _pm.open_progress(
        "EIS — Save", "Saving EIS data...", max(1, n),
    )
    try:
        EIS.backup_folder_to_temp_zip('EIS', 'EIS_backup.zip')
        _current_file = ""
        if config.selected_files:
            for i, file_name in enumerate(config.selected_files):
                _current_file = file_name
                _pm.update_progress(progress, i, file_name)
                try:
                    file_name_no_ext = os.path.splitext(file_name)[0]
                    config.store[file_name_no_ext]['EIS'].file_folder = config.folder_path
                    config.store[file_name_no_ext]['EIS'].save_data_EIS()
                except Exception as _ei:
                    import traceback as _tb
                    print(f"[Warning] EIS-save failed for {file_name}: {_ei}\n{_tb.format_exc()}")
                    _pm.show_error_dialog("EIS — Save Warning", f"'{file_name}' could not be saved:\n{_ei}")
                _pm.update_progress(progress, i + 1, file_name)
    except Exception as _e:
        import traceback as _tb
        print(f"[Error] EIS save_eis:\n{_tb.format_exc()}")
        _pm.close_progress(progress); progress = None
        _pm.show_error_dialog("EIS — Save Error", f"{type(_e).__name__}: {_e}", file_hint=_current_file)
    finally:
        _pm.close_progress(progress)