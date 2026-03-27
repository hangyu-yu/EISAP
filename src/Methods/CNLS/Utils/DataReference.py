"""Helpers for resolving CNLS reference data from EIS/DRT results."""

VALID_CNLS_BASE_DATA_TYPES = (
    "truncated",
    "smooth_KK",
    "smooth_DRT",
    "extrapolation",
    "LCcorrect",
)

DEFAULT_CNLS_DATA_TYPE = "truncated"


def get_cnls_data_type_items():
    """Return UI options for CNLS DRT-reference data selection."""
    return [
        "truncated",
        "truncated_RBF",
        "smooth_KK",
        "smooth_KK_RBF",
        "smooth_DRT",
        "smooth_DRT_RBF",
        "extrapolation",
        "extrapolation_RBF",
        "LCcorrect",
        "LCcorrect_RBF",
    ]


def _get_eis_item(eis_data, key):
    """Read a key from EIS-like objects (dict or __getitem__ class)."""
    try:
        return eis_data[key]
    except Exception:
        return getattr(eis_data, key, None)


def _is_valid_drt_result(result):
    if not isinstance(result, dict):
        return False
    reim = result.get("ReIm", None)
    if not isinstance(reim, dict):
        return False
    g = reim.get("g", None)
    has_axis = (
        reim.get("f", None) is not None
        or reim.get("f_gamma", None) is not None
        or reim.get("tau_gamma", None) is not None
    )
    return g is not None and has_axis


def _to_1d_array(values):
    if values is None:
        return None
    try:
        arr = values if hasattr(values, "shape") else list(values)
        import numpy as np

        return np.asarray(arr).reshape(-1)
    except Exception:
        return None


def _resolve_drt_axis_for_gamma(reim):
    """Resolve frequency axis matching gamma length.

    Priority:
    1) f (standard Tikhonov outputs)
    2) f_gamma (RBF fine grid)
    3) tau_gamma converted to frequency
    """
    drt_mes = _to_1d_array(reim.get("g", None))
    if drt_mes is None or len(drt_mes) == 0:
        return None, None

    def _valid_positive_axis(axis, n_expected):
        if axis is None or len(axis) != n_expected:
            return False
        import numpy as np

        return bool(np.all(np.isfinite(axis) & (axis > 0)))

    # Standard path (most Tikhonov outputs)
    drt_f = _to_1d_array(reim.get("f", None))
    if _valid_positive_axis(drt_f, len(drt_mes)):
        return drt_f, drt_mes

    # RBF fine-grid path
    drt_f_gamma = _to_1d_array(reim.get("f_gamma", None))
    if _valid_positive_axis(drt_f_gamma, len(drt_mes)):
        return drt_f_gamma, drt_mes

    # Fallback from tau_gamma
    tau_gamma = _to_1d_array(reim.get("tau_gamma", None))
    if tau_gamma is not None and len(tau_gamma) == len(drt_mes):
        import numpy as np

        with np.errstate(divide="ignore", invalid="ignore"):
            f_from_tau = 1.0 / (2.0 * np.pi * tau_gamma)
        if _valid_positive_axis(f_from_tau, len(drt_mes)):
            return f_from_tau, drt_mes

    return None, drt_mes


def normalize_cnls_data_type(data_type):
    """Normalize incoming CNLS data type and parse whether RBF is requested."""
    value = DEFAULT_CNLS_DATA_TYPE if data_type is None else str(data_type).strip()
    if value == "":
        value = DEFAULT_CNLS_DATA_TYPE

    if value == "LCcorrected":
        value = "LCcorrect"

    use_rbf = value.endswith("_RBF")
    base_type = value[:-4] if use_rbf else value

    if base_type == "LCcorrected":
        base_type = "LCcorrect"

    if base_type not in VALID_CNLS_BASE_DATA_TYPES:
        base_type = DEFAULT_CNLS_DATA_TYPE

    normalized = f"{base_type}_RBF" if use_rbf else base_type
    return normalized, base_type, use_rbf


def resolve_cnls_reference(eis_data, data_type, allow_rbf_fallback=True):
    """
    Resolve CNLS reference data for the chosen data_type.

    Returns a dict with DRT and impedance vectors for CNLS usage.
    Returns None when no valid reference can be resolved.
    """
    normalized_data_type, base_type, use_rbf = normalize_cnls_data_type(data_type)

    drt_suffix = base_type.replace("_KK", "").replace("_DRT", "")
    drt_suffix_for_signal = "truncated" if base_type == "smooth_DRT" else drt_suffix

    candidate_prefixes = ["rbf", "tknv"] if (use_rbf and allow_rbf_fallback) else (["rbf"] if use_rbf else ["tknv"])

    selected = None
    for prefix in candidate_prefixes:
        drt_key = f"{prefix}_{drt_suffix_for_signal}"
        drt_result = _get_eis_item(eis_data, drt_key)
        if not _is_valid_drt_result(drt_result):
            continue

        reim = drt_result.get("ReIm", {})
        drt_f, drt_mes = _resolve_drt_axis_for_gamma(reim)
        if drt_f is None or drt_mes is None or len(drt_f) == 0 or len(drt_mes) == 0:
            continue
        if len(drt_f) != len(drt_mes):
            continue

        if base_type == "smooth_KK":
            smooth_data = _get_eis_item(eis_data, "smooth")
            z_mes = smooth_data.get("Z", None) if isinstance(smooth_data, dict) else None
            z_f = smooth_data.get("f", None) if isinstance(smooth_data, dict) else None
        elif base_type == "smooth_DRT":
            reim = drt_result.get("ReIm", {})
            re_part = reim.get("Re", None)
            im_part = reim.get("Im", None)
            z_mes = re_part + 1j * im_part if re_part is not None and im_part is not None else None
            z_f = reim.get("f", None)
        else:
            eis_branch = _get_eis_item(eis_data, base_type.replace("_KK", ""))
            z_mes = eis_branch.get("Z", None) if isinstance(eis_branch, dict) else None
            z_f = eis_branch.get("f", None) if isinstance(eis_branch, dict) else None

        if z_mes is None:
            continue

        z_mes = _to_1d_array(z_mes)
        z_f = _to_1d_array(z_f)
        if z_mes is None or z_f is None or len(z_mes) == 0 or len(z_f) == 0:
            continue
        if len(z_mes) != len(z_f):
            continue

        drt_rl_key = f"{prefix}_{drt_suffix}"
        drt_rl_result = _get_eis_item(eis_data, drt_rl_key)
        if not isinstance(drt_rl_result, dict) or not isinstance(drt_rl_result.get("RL", None), dict):
            drt_rl_result = drt_result

        selected = {
            "normalized_data_type": f"{base_type}_RBF" if prefix == "rbf" else base_type,
            "base_type": base_type,
            "requested_rbf": use_rbf,
            "use_rbf": prefix == "rbf",
            "prefix": prefix,
            "drt_key": drt_key,
            "drt_rl_key": drt_rl_key,
            "drt_result": drt_result,
            "drt_rl_result": drt_rl_result,
            "z_f": z_f,
            "drt_f": drt_f,
            "f": z_f,
            "drt_mes": drt_mes,
            "z_mes": z_mes,
            "len_z": len(z_mes),
            "len_drt": len(drt_mes),
        }
        break

    if selected is None:
        return None

    # Keep normalized naming stable when a fallback was not needed.
    if selected["use_rbf"] == use_rbf:
        selected["normalized_data_type"] = normalized_data_type

    return selected