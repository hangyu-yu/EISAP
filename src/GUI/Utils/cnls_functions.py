import os
import copy
import math
import numpy as np
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils
import src.Methods.CNLS.Utils as CNLS_fn
from src.Methods.CNLS.Circuit import Circuit


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
    enable_state = (dpg.get_value("combo_peak_ID") == "fixed")
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

def peak_mode(sender, appdata, config):
    """Callback function for peak ID selection.
    
    Args:
        sender: Sender of the callback.
        appdata: Application data.
        config: Configuration object.
    """
    if appdata == "fixed":
        dpg.configure_item("input_nbr_peaks", enabled=True)
    else:
        dpg.configure_item("input_nbr_peaks", enabled=False)
    file_name_no_ext = os.path.splitext(config.display_file)[0]
    config.store[file_name_no_ext]['CNLS'].f_mode = appdata
    dynamic_peak_ids(sender, appdata, config)

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
            CNLS_tmp.f_mode = dpg.get_value("combo_peak_ID")
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
            CNLS_tmp.f_mode = dpg.get_value("combo_peak_ID")
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