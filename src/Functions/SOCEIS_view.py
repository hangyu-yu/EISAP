#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
_________________________________________________________________

                REQUIREMENTS & USAGE
_________________________________________________________________

This application is designed to analyze SOCEIS data.
Created date: 11.February.2026

Folder structure requirement:
You must have a main root folder (e.g. EIS/SIM/) containing
subfolders named "EIS", and optionally sibling folders
"DRT" and "CNLS", automatically generated from SOCEIS code.

The program automatically:
 - Detects all .xlsx files inside any "EIS" folder
 - Looks for matching filenames inside sibling "DRT"
   and "CNLS" folders (if present)

Required Python packages (install once):
   pip install streamlit pandas numpy plotly matplotlib openpyxl ast tkinter

 How to run the application:
   Open a terminal (PowerShell on Windows) in the folder
   containing this script and execute:

       streamlit run SOCEIS_view.py

The app will open automatically in your default browser.
_________________________________________________________________

"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from io import BytesIO
import zipfile
import re
import subprocess
import sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import colormaps
import plotly.colors as pc
from pathlib import Path
import argparse
import os

try:
    import tkinter as tk
    from tkinter import filedialog
    TK_AVAILABLE = True
except Exception:
    tk = None
    filedialog = None
    TK_AVAILABLE = False

# ===============================
# Helper function for Windows long path support
# ===============================
def _normalize_path(path_obj):
    """Handle Windows long path (260+ chars) by adding \\\\?\\ prefix."""
    path_str = str(path_obj)
    if sys.platform == 'win32' and os.path.isabs(path_str) and not path_str.startswith('\\\\'):
        return '\\\\?' + os.path.sep + os.path.abspath(path_str)
    return path_str

# ===============================
# Configuration
# ===============================


def ensure_email_prompt_disabled():
    try:
        config_path = Path.home() / ".streamlit" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")

            # If already set to false, do nothing
            if "showEmailPrompt = false" in content:
                return

            # If explicitly set to true, replace it
            if "showEmailPrompt = true" in content:
                content = content.replace(
                    "showEmailPrompt = true",
                    "showEmailPrompt = false"
                )
            else:
                # If the field does not exist, append it
                if "[general]" in content:
                    content += "\nshowEmailPrompt = false\n"
                else:
                    content += "\n[general]\nshowEmailPrompt = false\n"

            config_path.write_text(content, encoding="utf-8")

        else:
            # If config file does not exist, create it
            config_path.write_text(
                "[general]\nshowEmailPrompt = false\n",
                encoding="utf-8"
            )

    except Exception:
        # Fail silently to avoid breaking Streamlit startup
        pass


# Call before any Streamlit UI code
ensure_email_prompt_disabled()

parser = argparse.ArgumentParser()
parser.add_argument("--root_folder", type=str, default="")

try:
    args, _ = parser.parse_known_args()
    parsed_path = args.root_folder
except SystemExit:
    parsed_path = ""

if parsed_path:
    DEFAULT_ROOT_FOLDER = Path(parsed_path)
else:
    DEFAULT_ROOT_FOLDER = Path("EIS/SIM")

DEFAULT_EXPORT_FOLDER = Path(os.path.join(DEFAULT_ROOT_FOLDER, "SOCEIS_figures"))

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "axes.linewidth": 1.0,
    "lines.linewidth": 1.5,
    "figure.dpi": 300,
})

DEFAULT_COLOR_PALETTE = [
    "#4C78A8",  # blue
    "#F58518",  # orange
    "#54A24B",  # green
    "#E45756",  # red
    "#B279A2",  # purple
    "#FF9DA6",  # pink
    "#9D755D",  # brown
    "#BAB0AC",  # grey
    "#72B7B2",  # teal
    "#F2CF5B",  # yellow
]


# ===============================

EIS_PARAMETERS_SHEET = "EIS_Parameters"
DRT_PARAMETERS_SHEET = "DRT_Parameters"


NYQUIST_TYPES = [
    "Original",
    "Truncated",
    "LC corrected",
    "Linear Kramers-Kroning",
    "Smooth",
    "Extended",
]

DEFAULT_NYQUIST = ["Original", "Truncated"]

BODE_TYPES = NYQUIST_TYPES

DRT_TYPES = ["Truncated", "Smooth", "LCcorrect", "Extrapolation", "Z-HIT",
             "RBF", "RBF Smooth", "RBF LCcorrect", "RBF Extrapolation", "RBF Z-HIT"]
DRT_SHEET_MAP = {
    "Truncated": "Tknv_ReIm",
    "Smooth": "Tknv_ReIm_s",
    "LCcorrect": "Tknv_ReIm_crct",
    "Extrapolation": "Tknv_ReIm_e",
    "Z-HIT": "Tknv_ReIm_z",
    "RBF": "RBF_ReIm",
    "RBF Smooth": "RBF_s_ReIm",
    "RBF LCcorrect": "RBF_crct_ReIm",
    "RBF Extrapolation": "RBF_e_ReIm",
    "RBF Z-HIT": "RBF_z_ReIm",
}

# CNLS
CNLS_ENABLED_DEFAULT = False
CNLS_SHEET = "Elements"

def nyquist_fit_plotly(datasets):

    fig = go.Figure()
    show_legend = len(datasets) > 1
    for i, (name, df) in enumerate(datasets):

        x = pd.to_numeric(df.iloc[:, 2], errors="coerce")   # Re
        y = -pd.to_numeric(df.iloc[:, 3], errors="coerce")  # Im

        fig.add_scatter(
            x=x,
            y=y,
            mode="markers+lines",
            name=name,
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)])
        )

        fig.update_layout(
            title="Nyquist – DRT Smooth Fit",
            xaxis=dict(
                title="Z′ [Ω·cm²]",
                scaleanchor="y",
                scaleratio=1
            ),
            yaxis=dict(
                title="−Z″ [Ω·cm²]"
            ),
            template="plotly_dark",
            legend=dict(
                orientation="v",
                y=1,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=11)
            ) if show_legend else dict(visible=False)
        )

    return fig

def cnls_line_plotly(df_cnls: pd.DataFrame, param: str):

    x = np.arange(1, len(df_cnls) + 1)
    y = df_cnls[param].values
    x_labels = [str(idx) for idx in df_cnls.index.tolist()]

    mean_val = np.nanmean(y)
    std_val = np.nanstd(y)

    fig = go.Figure()

    # ---- Main resistance line (NO legend) ----
    fig.add_scatter(
        x=x,
        y=y,
        mode="lines",
        line=dict(width=3, color="white"),
        showlegend=False
    )

    # ---- Points + Legend mapping ----
    for i, (idx, val) in enumerate(zip(df_cnls.index.tolist(), y)):

        label = latex_label(idx)

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        fig.add_scatter(
            x=[i+1],
            y=[val],
            mode="markers",
            marker=dict(
                size=10,
                color="white",
                line=dict(width=2, color=color)
            ),
            name=f"{i+1} - {label}",
            showlegend=True
        )

    fig.update_layout(
        title=f"{param} — Mean value: {mean_val:.3g} | Std value: {std_val:.3g}",
        xaxis_title="File index",
        yaxis_title="R [Ω·cm²]",
        template="plotly_dark",
        legend=dict(
            orientation="v",
            font=dict(size=11)
        ),
        xaxis=dict(
            tickmode="array",
            tickvals=x.tolist(),
            ticktext=x_labels,
            tickangle=30,
            automargin=True,
        )
    )

    return fig




# EIS parameter mapping (restored)
EIS_PARAM_ORDER = [
    ("Cell area [cm²]", "CellArea/cm2"),
    ("Cell No.", "n_cell"),
    ("Instrument", "instrument_type"),
    ("Upper cut", "Nfh_cut"),
    ("Lower cut", "Nfl_cut"),
    ("Max. KK res. [%]", "kk_threshold"),
    ("Remove high KK resid.", "RmNonKK"),
    ("Remove outliers", "Rmoutliers"),
    ("Manual removal enabled", "ManualRemoval"),
    ("Manual removed indices", "ManualRemoval_Indices"),
    ("Rm significance", "rm_significance"),
    ("Z-HIT enabled", "ZHIT_enable"),
]


# ===============================
# Helpers
# ===============================

# ===============================
# Color palette selection
# ===============================

def _rgb_str_to_hex(s: str) -> str:
    # "rgb(12,34,56)" or "rgba(12,34,56,0.5)" -> "#0c2238"
    nums = s.strip().lower().replace("rgba(", "").replace("rgb(", "").replace(")", "").split(",")
    r, g, b = [int(float(x)) for x in nums[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"

PLOTLY_SEQ = {
    "Viridis (perceptual)": pc.sequential.Viridis,
    "Cividis (colorblind-friendly)": pc.sequential.Cividis,
    "Plasma (perceptual)": pc.sequential.Plasma,
    "Inferno (perceptual)": pc.sequential.Inferno,
    "Magma (perceptual)": pc.sequential.Magma,
    "Turbo (high-contrast)": pc.sequential.Turbo,
}

def sample_plotly_sequential(palette_choice: str, n: int, lo: float = 0.10, hi: float = 0.95) -> List[str]:
    """
    Sample a Plotly sequential colorscale to n HEX colors.
    lo/hi trim avoids the extreme darkest/brightest ends.
    """
    scale = PLOTLY_SEQ[palette_choice]  # list of "rgb(...)"
    if n <= 1:
        t_vals = [0.5]
    else:
        t_vals = np.linspace(lo, hi, n)
    rgb_list = pc.sample_colorscale(scale, t_vals)
    return [_rgb_str_to_hex(c) for c in rgb_list]

PALETTE_LIBRARY = {
    "Default": "SOCEIS_DEFAULT",
    "Viridis (perceptual)": "viridis",
    "Cividis (colorblind-friendly)": "cividis",
    "Plasma (perceptual)": "plasma",
    "Inferno (perceptual)": "inferno",
    "Magma (perceptual)": "magma",
    "Turbo (high-contrast)": "turbo",
    "Matplotlib tab10": "tab10",
    "Matplotlib tab20": "tab20",
    "Matplotlib Set2 (pastel)": "Set2",
    "Matplotlib Dark2": "Dark2",
    "Matplotlib Paired": "Paired",

}


def sample_palette_colors(palette_choice: str, n: int) -> List[str]:
    # Default
    if palette_choice == "Default":
        base = DEFAULT_COLOR_PALETTE
        if n <= len(base):
            return base[:n]
        return (base * ((n + len(base) - 1) // len(base)))[:n]

    # Plotly scientific sequential palettes
    if palette_choice in PLOTLY_SEQ:
        return sample_plotly_sequential(palette_choice, n=n, lo=0.10, hi=0.95)

    # Matplotlib qualitative (tab10/tab20/Set2/Dark2/Paired)
    cmap_name = PALETTE_LIBRARY.get(palette_choice, "tab10")
    cmap = colormaps.get_cmap(cmap_name)
    if hasattr(cmap, "colors") and cmap.colors is not None:
        base = [mcolors.to_hex(c) for c in cmap.colors]
        if n <= len(base):
            return base[:n]
        return (base * ((n + len(base) - 1) // len(base)))[:n]

    # fallback (shouldn't usually hit)
    return DEFAULT_COLOR_PALETTE[:n]

def render_palette_preview(colors: List[str]) -> str:
    swatches = "".join(
        f"<span style='display:inline-block;width:18px;height:18px;"
        f"margin-right:6px;border-radius:4px;border:1px solid rgba(255,255,255,0.35);"
        f"background:{c};'></span>"
        for c in colors
    )
    return f"<div style='margin-top:6px;margin-bottom:4px;'>{swatches}</div>"

def latex_label(text: str) -> str:

    # Explicit LaTeX patterns
    if (
        "\\" in text or
        "_{" in text or
        "^{" in text
    ):
        # Avoid double wrapping
        if text.startswith("$") and text.endswith("$"):
            return text
        return f"${text}$"

    return text


def _resolve_initial_dir(current_dir: Optional[str], fallback_dir: Optional[Path]) -> Optional[Path]:
    """Resolve initial dialog directory: current path first, then fallback path."""
    if current_dir:
        try:
            p = Path(current_dir).expanduser()
            if p.exists() and p.is_dir():
                return p
        except Exception:
            pass

    if fallback_dir is not None:
        try:
            fb = Path(fallback_dir).expanduser()
            if fb.exists() and fb.is_dir():
                return fb
        except Exception:
            pass

    return None


def pick_folder_dialog(current_dir: Optional[str] = None,
                       fallback_dir: Optional[Path] = None) -> Optional[str]:
    """Open a native folder picker and return selected path or None."""
    initial_dir = _resolve_initial_dir(current_dir, fallback_dir)

    # On macOS, Finder chooser via AppleScript is usually more reliable
    # than tkinter inside Streamlit's runtime.
    if sys.platform == "darwin":
        try:
            choose_expr = "choose folder with prompt \"Select project folder\""
            if initial_dir is not None:
                posix_dir = initial_dir.as_posix().replace('"', '\\"')
                choose_expr += f' default location (POSIX file "{posix_dir}")'

            cmd = ["osascript", "-e", "try",
                   "-e", f"POSIX path of ({choose_expr})",
                   "-e", "on error number -128",
                   "-e", "return \"\"",
                   "-e", "end try"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            folder = (result.stdout or "").strip()
            # On macOS, canceling the Finder dialog should simply return None.
            # Do not fall back to tkinter in this case, as it can terminate the
            # Streamlit process in some runtime environments.
            return folder if folder else None
        except Exception:
            return None

    if not TK_AVAILABLE:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # bring dialog to front
    ask_kwargs = {}
    if initial_dir is not None:
        ask_kwargs["initialdir"] = str(initial_dir)
    folder = filedialog.askdirectory(**ask_kwargs)
    root.destroy()

    return folder if folder else None

def yes_no(v) -> str:
    return "Yes" if str(v).lower() in ("1", "true", "yes") else "No"


def discover_eis_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for eis_dir in root.rglob("EIS"):
        if eis_dir.is_dir():
            files.extend(sorted(eis_dir.glob("*.xlsx")))
    return files


def compress_indices(value) -> str:
    """
    Convert '1,2,3,4,5,6,7,8,9,10,37,41,42,43'
    -> '1-10,37,41-43'
    """

    if pd.isna(value):
        return ""

    try:
        nums = sorted(int(x.strip()) for x in str(value).split(",") if x.strip().isdigit())
    except Exception:
        return str(value)

    if not nums:
        return ""

    ranges = []
    start = nums[0]
    prev = nums[0]

    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = prev = n

    ranges.append(f"{start}-{prev}" if start != prev else f"{start}")

    return ",".join(ranges)



def natural_key(s: str):
    """
    Natural sort key: 's2' < 's10', case-insensitive.
    Splits into text + number chunks.
    """
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def sibling_file(eis_file: Path, sibling_folder: str) -> Path:
    """
    sibling_folder is e.g. "DRT" or "CNLS".
    Assumption: .../<parent>/EIS/<file>.xlsx and .../<parent>/<sibling_folder>/<file>.xlsx
    """
    eis_dir = eis_file.parent          # .../EIS
    parent_dir = eis_dir.parent        # .../
    return parent_dir / sibling_folder / eis_file.name


def extract_eis_parameters(xls: pd.ExcelFile, fname: str) -> Dict:
    row = {"File": fname}
    if EIS_PARAMETERS_SHEET not in xls.sheet_names:
        for label, _ in EIS_PARAM_ORDER:
            row[label] = None
        return row

    df = pd.read_excel(xls, EIS_PARAMETERS_SHEET)
    for label, key in EIS_PARAM_ORDER:
        if key in df.columns:
            val = df[key].iloc[0]

            if key in ("RmNonKK", "Rmoutliers", "ManualRemoval", "rm_significance", "ZHIT_enable"):
                val = yes_no(val)

            if key == "ManualRemoval_Indices":
                val = compress_indices(val)

            row[label] = val
        else:
            row[label] = None
    return row

def has_drt_fit(files_to_process: List[Path]) -> bool:
    """
    True if at least one selected EIS file has a sibling DRT file
    containing the DRT-fit sheet 'Tknv_ReIm_s' with >= 4 columns.
    """
    for eis_file in files_to_process:
        drt_file = sibling_file(eis_file, "DRT")
        if not drt_file.exists():
            continue
        try:
            xls = pd.ExcelFile(_normalize_path(drt_file))
            if "Tknv_ReIm_s" in xls.sheet_names:
                df = pd.read_excel(xls, "Tknv_ReIm_s")
                if df.shape[1] >= 4:
                    return True
        except Exception:
            continue
    return False

def extract_drt_lambda(drt_xls: pd.ExcelFile, fname: str) -> Optional[Dict]:

    if DRT_PARAMETERS_SHEET not in drt_xls.sheet_names:
        return None

    df = pd.read_excel(drt_xls, DRT_PARAMETERS_SHEET)

    if not len(df):
        return None

    lam = df["lambda"].iloc[0] if "lambda" in df.columns else None

    # --- Read tknv_pos ---
    if "tknv_pos" in df.columns:
        tknv_pos_raw = df["tknv_pos"].iloc[0]
        tknv_pos = bool(tknv_pos_raw)
    else:
        tknv_pos = False

    rbf_enabled = bool(df["rbf_enabled"].iloc[0]) if "rbf_enabled" in df.columns else False

    return {
        "File": fname,
        "lambda": lam,
        "tknv_pos": tknv_pos,
        "rbf_enabled": rbf_enabled,
    }

def _drt_ymax_from_datasets(datasets) -> float:
    global_max = 0.0
    for _, df in datasets:
        if df.shape[1] < 2:
            continue
        gamma = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        gamma = gamma[np.isfinite(gamma)]
        if len(gamma):
            m = float(gamma.max())
            if m > global_max:
                global_max = m
    return 1.15 * global_max if global_max > 0 else 1.0


def extract_cnls_parameters(cnls_file: Path) -> Optional[Dict[str, float]]:

    if not cnls_file.exists():
        return None

    try:
        xls = pd.ExcelFile(_normalize_path(cnls_file))
    except Exception:
        return None

    if CNLS_SHEET not in xls.sheet_names:
        return None

    df = pd.read_excel(xls, CNLS_SHEET)

    if df.shape[1] < 2:
        return None

    names = df.iloc[:, 0].astype(str).str.strip()
    vals = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    result: Dict[str, float] = {}

    # ---- R_ohmic ----
    mask_ohm = names == "R2_R"
    if mask_ohm.any():
        result["R_ohmic"] = float(vals[mask_ohm].iloc[0])
    else:
        result["R_ohmic"] = np.nan

    # ---- Dynamic RQ extraction ----
    for name, value in zip(names, vals):

        if pd.isna(value):
            continue

        # RQn_R
        match_r = re.match(r"RQ(\d+)_R$", name)
        if match_r:
            idx = int(match_r.group(1))
            result[f"R{idx}"] = float(value)
            continue

        # RQn_tau0
        match_tau = re.match(r"RQ(\d+)_tau0$", name)
        if match_tau:
            idx = int(match_tau.group(1))
            result[f"tau{idx}"] = float(value)
            continue

        # RQn_alpha
        match_alpha = re.match(r"RQ(\d+)_alpha$", name)
        if match_alpha:
            idx = int(match_alpha.group(1))
            result[f"alpha{idx}"] = float(value)
            continue

    # ---- Compute ASR (only R values) ----
    r_values = [v for k, v in result.items() if k.startswith("R")]
    result["ASR"] = float(np.nansum(r_values)) if r_values else np.nan

    return result


# ===============================
# Plotly builders (interactive)
# ===============================
def nyquist_plotly(datasets, title):

    fig = go.Figure()

    for i, (name, df) in enumerate(datasets):
        fig.add_scatter(
            x=pd.to_numeric(df.iloc[:, 1], errors="coerce"),
            y=-pd.to_numeric(df.iloc[:, 2], errors="coerce"),
            mode="markers+lines",
            name=name,
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        )

    fig.update_layout(
        title=title,
        xaxis=dict(
            title="Z′ [Ω·cm²]",
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            title="−Z″ [Ω·cm²]"
        ),
        template="plotly_dark",
        height=650  # enforce square aspect visually
    )

    return fig

def nyquist_compare_plotly(compare_mode, files_to_process, display_name_map):

    fig = go.Figure()

    mapping = {
        "Truncated vs Original": ("Truncated", "Original"),
        "Smooth vs Truncated": ("Truncated", "Smooth"),
        "LC corrected vs Truncated": ("Truncated", "LC corrected"),
        "Extended vs Truncated": ("Truncated", "Extended"),
        "DRT Fit vs Truncated": ("Truncated", "DRT Fit")
    }

    sheet_trunc, sheet_other = mapping[compare_mode]

    for i, eis_file in enumerate(files_to_process):

        fname = eis_file.name
        label = latex_label(display_name_map.get(fname, fname))
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        xls = pd.ExcelFile(_normalize_path(eis_file))

        # -------------------------
        # Load Truncated (always needed)
        # -------------------------
        df_trunc = None
        if sheet_trunc in xls.sheet_names:
            df_trunc = pd.read_excel(xls, sheet_trunc)

        # -------------------------
        # Load comparison dataset
        # -------------------------
        df_other = None

        if sheet_other == "DRT Fit":
            drt_file = sibling_file(eis_file, "DRT")
            if drt_file.exists():
                drt_xls = pd.ExcelFile(_normalize_path(drt_file))
                if "Tknv_ReIm_s" in drt_xls.sheet_names:
                    df_other = pd.read_excel(drt_xls, "Tknv_ReIm_s")
        else:
            if sheet_other in xls.sheet_names:
                df_other = pd.read_excel(xls, sheet_other)

        if df_trunc is None:
            continue

        # ============================================================
        # CASE 1 → Truncated vs Original
        # ============================================================
        if compare_mode == "Truncated vs Original":

            # ---- Original FIRST (transparent hollow circles)
            if df_other is not None:
                fig.add_scatter(
                    x=pd.to_numeric(df_other.iloc[:, 1], errors="coerce"),
                    y=-pd.to_numeric(df_other.iloc[:, 2], errors="coerce"),
                    mode="markers",
                    marker=dict(
                        size=7,
                        symbol="circle",
                        color="rgba(0,0,0,0)",      # transparent fill
                        line=dict(width=2, color=color),
                        opacity=0.5
                    ),
                    name=f"{label} - Original"
                )

            # ---- Truncated SECOND (solid filled circles)
            fig.add_scatter(
                x=pd.to_numeric(df_trunc.iloc[:, 1], errors="coerce"),
                y=-pd.to_numeric(df_trunc.iloc[:, 2], errors="coerce"),
                mode="markers",
                marker=dict(
                    size=7,
                    symbol="circle",
                    color=color,
                    opacity=1.0,
                    line=dict(width=1, color=color)
                ),
                name=f"{label} - Truncated"
            )

        # ============================================================
        # CASE 2 → X vs Truncated
        # ============================================================
        else:

            # ---- Truncated (filled markers, NO legend)
            fig.add_scatter(
                x=pd.to_numeric(df_trunc.iloc[:, 1], errors="coerce"),
                y=-pd.to_numeric(df_trunc.iloc[:, 2], errors="coerce"),
                mode="markers",
                marker=dict(
                    size=6,
                    symbol="circle",
                    color=color,
                    opacity=1.0,
                    line=dict(width=1, color=color)
                ),
                showlegend=False  # <-- important
            )

            if df_other is not None:

                if sheet_other == "DRT Fit":
                    xcol = 2
                    ycol = 3
                else:
                    xcol = 1
                    ycol = 2

                # ---- Comparison curve (LINE only, appears in legend)
                fig.add_scatter(
                    x=pd.to_numeric(df_other.iloc[:, xcol], errors="coerce"),
                    y=-pd.to_numeric(df_other.iloc[:, ycol], errors="coerce"),
                    mode="lines",
                    line=dict(width=3, color=color),
                    name=label  # <-- ONLY filename in legend
                )

    fig.update_layout(
        title=f"Nyquist Compare – {compare_mode}",
        xaxis=dict(
            title="Z′ [Ω·cm²]",
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(title="−Z″ [Ω·cm²]"),
        template="plotly_dark"
    )

    return fig

def bode_plotly(datasets, title, real=True):
    fig = go.Figure()
    for i, (name, df) in enumerate(datasets):
        x = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        y = pd.to_numeric(df.iloc[:, 1], errors="coerce") if real else -pd.to_numeric(df.iloc[:, 2], errors="coerce")
        fig.add_scatter(
            x=x,
            y=y,
            mode="lines",
            name=name,
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        )
    fig.update_layout(
        title="",
        xaxis=dict(title="Frequency [Hz]", type="log"),
        yaxis_title="Z′ [Ω·cm²]" if real else "−Z″ [Ω·cm²]",
        template="plotly_dark",
    )
    return fig


def zhit_plotly(datasets, mode: str = "modulus"):
    """
    Plot Z-HIT results.
    mode: "modulus"  → |Z| measured (markers) vs Z-HIT reconstructed (line)
          "phase"    → φ measured (markers) vs φ smoothed (dashed line)
          "delta"    → Δln|Z| deviation [%] per frequency
    ZHIT sheet columns:
      0 Frequency/Hz, 1 omega/rad/s, 2 Z_mod_meas/ohm·cm2,
      3 Z_mod_zhit/ohm·cm2, 4 phi_deg, 5 phi_smooth_deg,
      6 phase_integral, 7 correction, 8 delta_lnZ, 9 delta_lnZ_pct
    """
    fig = go.Figure()
    for i, (name, df) in enumerate(datasets):
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")

        if mode == "modulus":
            y_meas = pd.to_numeric(df.iloc[:, 2], errors="coerce")
            y_zhit = pd.to_numeric(df.iloc[:, 3], errors="coerce")
            fig.add_scatter(
                x=freq, y=y_meas, mode="markers",
                name=f"{name} – meas",
                legendgroup=name,
                marker=dict(size=4, color=color, opacity=0.6),
            )
            fig.add_scatter(
                x=freq, y=y_zhit, mode="lines",
                name=f"{name} – Z-HIT",
                legendgroup=name,
                line=dict(color=color, width=2),
            )
        elif mode == "phase":
            phi_meas   = pd.to_numeric(df.iloc[:, 4], errors="coerce")
            phi_smooth = pd.to_numeric(df.iloc[:, 5], errors="coerce")
            fig.add_scatter(
                x=freq, y=phi_meas, mode="markers",
                name=f"{name} – φ meas",
                legendgroup=name,
                marker=dict(size=4, color=color, opacity=0.6),
            )
            fig.add_scatter(
                x=freq, y=phi_smooth, mode="lines",
                name=f"{name} – φ smooth",
                legendgroup=name,
                line=dict(color=color, width=2, dash="dash"),
            )
        elif mode == "delta":
            delta_pct = pd.to_numeric(df.iloc[:, 9], errors="coerce")
            fig.add_scatter(
                x=freq, y=delta_pct, mode="lines+markers",
                name=name,
                line=dict(color=color, width=2),
                marker=dict(size=4, color=color),
            )

    if mode == "modulus":
        fig.update_layout(
            title="Z-HIT – |Z| comparison",
            xaxis=dict(title="Frequency [Hz]", type="log"),
            yaxis=dict(title="|Z| [Ω·cm²]", type="log"),
            template="plotly_dark",
        )
    elif mode == "phase":
        fig.update_layout(
            title="Z-HIT – Phase",
            xaxis=dict(title="Frequency [Hz]", type="log"),
            yaxis=dict(title="φ [°]"),
            template="plotly_dark",
        )
    elif mode == "delta":
        fig.update_layout(
            title="Z-HIT – ln|Z| deviation [%]",
            xaxis=dict(title="Frequency [Hz]", type="log"),
            yaxis=dict(title="Δln|Z| [%]"),
            template="plotly_dark",
        )
    return fig


def drt_plotly(datasets, title):
    fig = go.Figure()
    ymax = _drt_ymax_from_datasets(datasets)

    for i, (name, df) in enumerate(datasets):
        freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        gamma = pd.to_numeric(df.iloc[:, 1], errors="coerce")

        fig.add_scatter(
            x=freq,
            y=gamma,
            mode="lines",
            name=name,
            line=dict(color=COLOR_PALETTE[i % len(COLOR_PALETTE)]),
        )

    fig.update_layout(
        title=f"DRT – {title}",
        xaxis=dict(title="Frequency [Hz]", type="log"),
        yaxis=dict(title="γ [Ω·s·cm²]", range=[0, ymax]),
        template="plotly_dark",
    )
    return fig

def nyquist_3d_plotly(datasets, title):
    fig = go.Figure()

    # --- gather global ranges for true equal-unit scaling ---
    all_x = []
    all_z = []
    for _, df in datasets:
        x = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy()
        z = (-pd.to_numeric(df.iloc[:, 2], errors="coerce")).to_numpy()
        all_x.append(x)
        all_z.append(z)

    all_x = np.concatenate([v[np.isfinite(v)] for v in all_x]) if all_x else np.array([])
    all_z = np.concatenate([v[np.isfinite(v)] for v in all_z]) if all_z else np.array([])

    # avoid zero ranges
    xmin, xmax = (float(np.min(all_x)), float(np.max(all_x))) if all_x.size else (0.0, 1.0)
    zmin, zmax = (float(np.min(all_z)), float(np.max(all_z))) if all_z.size else (0.0, 1.0)


    # --- plot traces ---
    for i, (name, df) in enumerate(datasets):
        x = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        z = -pd.to_numeric(df.iloc[:, 2], errors="coerce")
        y_spacing = 1.0
        y = np.full_like(x, i * y_spacing)

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        # markers
        if not st.session_state.get("export_no_nyquist_markers", False):
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode="markers",
                marker=dict(size=3, color=color, opacity=0.6),
                showlegend=False
            ))

        # line
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode="lines",
            name=name,
            line=dict(color=color, width=4)
        ))
    x_range = max(xmax - xmin, 1e-12)
    z_range = max(zmax - zmin, 1e-12)    
    fig.update_layout(
        title=title,
        template="plotly_dark",
        scene=dict(
            xaxis=dict(title="Z′ [Ω·cm²]",autorange="reversed"),
            yaxis=dict(title="", showticklabels=False),
            zaxis=dict(title="−Z″ [Ω·cm²]"),
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=0.05 * len(datasets),                     # arbitrary thin stacking axis
                z=z_range / x_range         # THIS enforces equal units
            ),

            camera=dict(
                eye=dict(
                    x=-1.7,
                    y=1.7,
                    z=1.7
                )
            )
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig

def nyquist_3d_plotly_cols(datasets, title, x_col: int, y_col: int, negate_y: bool = True):
    fig = go.Figure()

    # gather global ranges for equal-unit scaling
    all_x = []
    all_z = []
    for _, df in datasets:
        x = pd.to_numeric(df.iloc[:, x_col], errors="coerce").to_numpy()
        zraw = pd.to_numeric(df.iloc[:, y_col], errors="coerce").to_numpy()
        z = (-zraw) if negate_y else zraw
        all_x.append(x)
        all_z.append(z)

    all_x = np.concatenate([v[np.isfinite(v)] for v in all_x]) if all_x else np.array([])
    all_z = np.concatenate([v[np.isfinite(v)] for v in all_z]) if all_z else np.array([])

    xmin, xmax = (float(np.min(all_x)), float(np.max(all_x))) if all_x.size else (0.0, 1.0)
    zmin, zmax = (float(np.min(all_z)), float(np.max(all_z))) if all_z.size else (0.0, 1.0)

    # plot traces
    for i, (name, df) in enumerate(datasets):
        x = pd.to_numeric(df.iloc[:, x_col], errors="coerce")
        zraw = pd.to_numeric(df.iloc[:, y_col], errors="coerce")
        z = -zraw if negate_y else zraw
        y_spacing = 1.0
        y = np.full_like(x, i * y_spacing)

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        if not st.session_state.get("export_no_nyquist_markers", False):
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode="markers",
                marker=dict(size=3, color=color, opacity=0.6),
                showlegend=False
            ))

        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode="lines",
            name=name,
            line=dict(color=color, width=4)
        ))
    x_range = max(xmax - xmin, 1e-12)
    z_range = max(zmax - zmin, 1e-12)    
    fig.update_layout(
        title=title,
        template="plotly_dark",
        scene=dict(
            xaxis=dict(title="Z′ [Ω·cm²]",autorange="reversed"),
            yaxis=dict(title="", showticklabels=False),
            zaxis=dict(title="−Z″ [Ω·cm²]"),
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=0.05*len(datasets),                     # arbitrary thin stacking axis
                z=z_range / x_range         # THIS enforces equal units
            ),

            camera=dict(
                eye=dict(
                    x=-1.7,
                    y=1.7,
                    z=1.7
                )
            )
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig

def drt_3d_plotly(datasets, title):

    fig = go.Figure()

    for i, (name, df) in enumerate(datasets):

        freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        gamma = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        y = np.full_like(freq, i)

        fig.add_trace(go.Scatter3d(
            x=freq,
            y=y,
            z=gamma,
            showlegend=True,
            mode="lines",  #  no markers
            name=name,
            line=dict(
                color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                width=4
            )
        ))

    fig.update_layout(
        title=title,
        template="plotly_dark",

        scene=dict(
            xaxis=dict(
                title="Frequency [Hz]",
                type="log",

                # Clean scientific ticks
                dtick=1,                 # one tick per decade
                tickformat=".1g",        # clean numeric format
                exponentformat="power",  # 10^x style if needed
                showexponent="all",
                autorange="reversed",
            ),

            yaxis=dict(
                title="",
                showticklabels=False
            ),
            zaxis=dict(
                title="γ [Ω·cm²·s]"
            ),

            #  Match Nyquist 3D proportions
            aspectmode="manual",
            aspectratio=dict(x=1.2, y=0.05*len(datasets), z=0.9),

            #  Same camera as Nyquist
            camera=dict(
                eye=dict(x=-1.4, y=1.4, z=1.4)
            )
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig


def cnls_nyquist_fit_plotly(cnls_file: Path, fname: str):

    if not cnls_file.exists():
        return None

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "Z" not in xls.sheet_names or "Summary" not in xls.sheet_names:
        return None

    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))

    df = pd.read_excel(xls, "Z")

    # ---- Main Nyquist ----
    z_real_total = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    z_imag_total = -pd.to_numeric(df.iloc[:, 2], errors="coerce")

    fig = go.Figure()

    fig.add_scatter(
        x=z_real_total,
        y=z_imag_total,
        mode="lines+markers",
        marker=dict(size=4),
        name="Total Z",
        line=dict(color="white", width=3)
    )

    # ---- Ohmic real column (col 12 -> index 11)
    z_ohmic = pd.to_numeric(df.iloc[:, 11], errors="coerce")
    offset = z_ohmic.iloc[-1]  # last value only

    start_col = 13
    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=len(rq_elements)
    )
    for i, rq in enumerate(rq_elements):

        real_col = start_col + 2*i
        imag_col = start_col + 2*i + 1

        if imag_col >= df.shape[1]:
            break

        z_r = pd.to_numeric(df.iloc[:, real_col], errors="coerce")
        z_i = -pd.to_numeric(df.iloc[:, imag_col], errors="coerce")

        # Shift by offset (constant shift)
        shifted_real = z_r + offset

        fig.add_scatter(
            x=shifted_real,
            y=z_i,
            mode="lines",
            name=rq,
            line=dict(color=element_colors[i])
        )

        # Update offset using LAST value of this element real part
        offset += z_r.iloc[-1]

        fig.update_layout(
            title=f"CNLS Nyquist Fit – {fname}",
            xaxis=dict(
                title="Z′ [Ω·cm²]",
                scaleanchor="y",
                scaleratio=1
            ),
            yaxis=dict(title="−Z″ [Ω·cm²]"),
            legend=dict(
                orientation="v",
                y=1,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=11)
            ),
            template="plotly_dark"
        )

    return fig

def cnls_residuals_plotly(cnls_file: Path, fname: str):

    if not cnls_file.exists():
        return None

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "Z" not in xls.sheet_names:
        return None

    df = pd.read_excel(xls, "Z")

    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    res_real = 100 * pd.to_numeric(df.iloc[:, 7], errors="coerce")
    res_imag = 100 * pd.to_numeric(df.iloc[:, 8], errors="coerce")

    fig = go.Figure()

    fig.add_scatter(
        x=freq,
        y=res_real,
        mode="lines+markers",
        marker=dict(size=6),
        name="Real residual",
        line=dict(color=COLOR_PALETTE[0])
    )

    fig.add_scatter(
        x=freq,
        y=res_imag,
        mode="lines+markers",
        marker=dict(size=6),
        name="Imag residual",
        line=dict(color=COLOR_PALETTE[1])
    )

    fig.update_layout(
        title=f"Nyquist Residuals – {fname}",
        xaxis=dict(title="Frequency [Hz]", type="log"),
        yaxis=dict(title="Residual [%]"),
        template="plotly_dark"
    )

    return fig

def cnls_bar_plotly(series: pd.Series):

    # Detect all Rn columns dynamically (excluding R_ohmic)
    r_keys = sorted(
        [k for k in series.index if k.startswith("R") and k != "R_ohmic"],
        key=lambda x: int(x[1:])
    )

    # Reverse order so highest index appears first
    r_keys = list(reversed(r_keys))

    order = ["ASR", "R_ohmic"] + r_keys

    y = [series.get(k, np.nan) for k in order]

    fig = go.Figure()
    fig.add_bar(
        x=order,
        y=y,
        showlegend=False
    )

    fig.update_layout(
        title="CNLS bar plot",
        xaxis_title="Parameter",
        yaxis_title="R [Ω·cm²]",
        yaxis_type="log",
        template="plotly_dark",
    )

    return fig

def cnls_elements_fitting_plotly(cnls_file: Path, fname: str):

    if not cnls_file.exists():
        return None

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "DRT" not in xls.sheet_names or "Summary" not in xls.sheet_names:
        return None

    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]  # A2 cell
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))

    df = pd.read_excel(xls, "DRT")

    # Need at least: freq(0), total(1), ... contributions start at col 5
    if df.shape[1] <= 5:
        return None

    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    gamma_total = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    fig = go.Figure()
    fig.add_scatter(
        x=freq,
        y=gamma_total,
        mode="lines",
        name="Total γ",
        line=dict(color="white", width=3)
    )

    # How many contribution columns actually exist?
    contrib_start = 5
    n_available = df.shape[1] - contrib_start
    n_use = min(len(rq_elements), n_available)

    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=max(1, n_use)
    )

    for i in range(n_use):
        rq = rq_elements[i]
        gamma_elem = pd.to_numeric(df.iloc[:, contrib_start + i], errors="coerce")

        fig.add_scatter(
            x=freq,
            y=gamma_elem,
            mode="lines",
            name=rq,
            line=dict(color=element_colors[i])
        )
    
    # Optional: warn in the UI if mismatch (helps debugging)
    if len(rq_elements) > n_available:
        dropped = ", ".join(rq_elements[n_available:])
        st.warning(
            f"Summary lists {len(rq_elements)} RQ elements but DRT sheet provides only "
            f"{n_available} contribution columns.\n\n"
            f"Plotted: {', '.join(rq_elements[:n_available])}\n"
            f"Omitted: {dropped}"
        )

    fig.update_layout(
        title=f"CNLS DRT Fit – {fname}",
        xaxis=dict(title="Frequency [Hz]", type="log"),
        yaxis=dict(title="γ [Ω·s·cm²]"),
        template="plotly_dark"
    )

    return fig

def cnls_elements_im_bode_plotly(cnls_file: Path, fname: str):

    if not cnls_file.exists():
        return None

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "Z" not in xls.sheet_names or "Summary" not in xls.sheet_names:
        return None

    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))

    df = pd.read_excel(xls, "Z")

    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    zmes_im = -pd.to_numeric(df.iloc[:, 2], errors="coerce")

    fig = go.Figure()

    fig.add_scatter(
        x=freq,
        y=zmes_im,
        mode="markers",
        marker=dict(size=5, color="white"),
        name="Measure"
    )

    # Map RQn → imaginary column using header names (robust to circuit variations)
    rq_im_map = {}
    for col in df.columns:
        m = re.match(r"(RQ\d+)_Im", col)
        if m:
            rq_im_map[m.group(1)] = col

    n_elems = sum(1 for rq in rq_elements if rq in rq_im_map)
    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=max(1, n_elems)
    )

    color_idx = 0
    for rq in rq_elements:
        if rq not in rq_im_map:
            continue
        z_im = -pd.to_numeric(df[rq_im_map[rq]], errors="coerce")
        fig.add_scatter(
            x=freq,
            y=z_im,
            mode="lines",
            name=rq,
            line=dict(color=element_colors[color_idx])
        )
        color_idx += 1

    fig.update_layout(
        title=f"Imaginary Bode – {fname}",
        xaxis=dict(title="Frequency [Hz]", type="log"),
        yaxis=dict(title="−Z″ [Ω·cm²]"),
        template="plotly_dark"
    )

    return fig

def cnls_heatmap_plotly(df_cnls: pd.DataFrame, palette_choice: str, param_groups=None):
    """Return a list of heatmap figures for the requested param_groups.

    param_groups is a subset of ["R", "Time constant", "Alpha"].
    Defaults to all three when None.
    """
    if param_groups is None:
        param_groups = ["R", "Time constant", "Alpha"]

    if palette_choice in PLOTLY_SEQ:
        colorscale = palette_choice.split(" ")[0]
    else:
        colorscale = "Viridis"

    y_labels = [latex_label(i) for i in df_cnls.index.tolist()]
    r_indices = sorted(
        {int(k[1:]) for k in df_cnls.columns if k.startswith("R") and k != "R_ohmic"}
    )

    figures = []

    # ---- Resistances (log scale) ----
    if "R" in param_groups:
        r_cols = [f"R{i}" for i in r_indices if f"R{i}" in df_cnls.columns]
        r_col_order = [c for c in ["ASR", "R_ohmic"] + r_cols if c in df_cnls.columns]
        if r_col_order:
            data = df_cnls[r_col_order].values.astype(float)
            data[data <= 0] = np.nan
            x_labels = ["R<sub>ohmic</sub>" if c == "R_ohmic" else c for c in r_col_order]
            fig = go.Figure(go.Heatmap(
                z=np.log10(data), x=x_labels, y=y_labels,
                colorscale=colorscale, xgap=2, ygap=2,
                colorbar=dict(title=dict(text="log(R [Ω·cm²])", side="right"))
            ))
            fig.update_layout(
                title="CNLS resistances heatmap", template="plotly_dark",
                xaxis_title="Parameter", yaxis_title="File",
            )
            figures.append(fig)

    # ---- Time constants (log scale) ----
    if "Time constant" in param_groups:
        tau_cols = [f"tau{i}" for i in r_indices if f"tau{i}" in df_cnls.columns]
        if tau_cols:
            data = df_cnls[tau_cols].values.astype(float)
            data[data <= 0] = np.nan
            x_labels = [f"τ<sub>{c[3:]}</sub>" for c in tau_cols]
            fig = go.Figure(go.Heatmap(
                z=np.log10(data), x=x_labels, y=y_labels,
                colorscale=colorscale, xgap=2, ygap=2,
                colorbar=dict(title=dict(text="log(τ [s])", side="right"))
            ))
            fig.update_layout(
                title="CNLS time constants heatmap", template="plotly_dark",
                xaxis_title="Parameter", yaxis_title="File",
            )
            figures.append(fig)

    # ---- Dispersion factors (linear 0–1) ----
    if "Alpha" in param_groups:
        alpha_cols = [f"alpha{i}" for i in r_indices if f"alpha{i}" in df_cnls.columns]
        if alpha_cols:
            data = df_cnls[alpha_cols].values.astype(float)
            x_labels = [f"α<sub>{c[5:]}</sub>" for c in alpha_cols]
            fig = go.Figure(go.Heatmap(
                z=data, x=x_labels, y=y_labels,
                colorscale=colorscale, zmin=0, zmax=1, xgap=2, ygap=2,
                colorbar=dict(title=dict(text="α", side="right"))
            ))
            fig.update_layout(
                title="CNLS dispersion factors heatmap", template="plotly_dark",
                xaxis_title="Parameter", yaxis_title="File",
            )
            figures.append(fig)

    return figures





# ===============================
# Matplotlib → write PNG bytes directly into ZIP
# ===============================
def _fig_to_bytes(fig, fmt: str) -> bytes:
    """
    Export matplotlib figure to selected format.
    """
    buf = BytesIO()

    if fmt == "pdf":
        fig.savefig(buf, format="pdf", bbox_inches="tight", pad_inches=0.2)
    else:
        fig.savefig(buf, format=fmt, dpi=300, bbox_inches="tight", pad_inches=0.2)

    plt.close(fig)
    return buf.getvalue()

def add_nyquist_png(zf: zipfile.ZipFile, datasets, title: str):

    fig, ax = plt.subplots(figsize=(6, 6), dpi=600)

    all_x = []
    all_y = []

    for i, (name, df) in enumerate(datasets):
        x = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        y = -pd.to_numeric(df.iloc[:, 2], errors="coerce")

        if not st.session_state.get("export_no_nyquist_markers", False):
            ax.plot(
                x, y,
                linestyle='None',
                marker='o',
                markersize=3,
                markerfacecolor=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                markeredgecolor=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                alpha=0.6
            )

        ax.plot(
            x, y,
            linewidth=1.5,
            color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
            alpha=0.85,
            label=latex_label(name)
        )

        all_x.extend(x.dropna())
        all_y.extend(y.dropna())

    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)

        margin_x = (xmax - xmin) * 0.03
        margin_y = (ymax - ymin) * 0.03

        ax.set_xlim(xmin - margin_x, xmax + margin_x)

        if ymin < 0:
            ax.set_ylim(ymin - margin_y, ymax + margin_y)
        else:
            ax.set_ylim(0, ymax + margin_y)

    ax.set_xlabel("Z′ [Ω·cm²]")
    ax.set_ylabel("−Z″ [Ω·cm²]")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    ax.set_aspect('equal', adjustable='box')
    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )
        fig.subplots_adjust(right=0.75)

        fig.subplots_adjust(bottom=0.22)
    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"Nyquist/{title}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )
    
def add_nyquist_compare_png(
    zf: zipfile.ZipFile,
    compare_mode: str,
    files_to_process,
    display_name_map
):

    fig, ax = plt.subplots(figsize=(6, 6), dpi=600)

    mapping = {
        "Truncated vs Original": ("Truncated", "Original"),
        "Smooth vs Truncated": ("Truncated", "Smooth"),
        "LC corrected vs Truncated": ("Truncated", "LC corrected"),
        "Extended vs Truncated": ("Truncated", "Extended"),
        "DRT Fit vs Truncated": ("Truncated", "DRT Fit")
    }

    sheet_trunc, sheet_other = mapping[compare_mode]

    all_x = []
    all_y = []

    for i, eis_file in enumerate(files_to_process):

        fname = eis_file.name
        label = latex_label(display_name_map.get(fname, fname))
        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        xls = pd.ExcelFile(_normalize_path(eis_file))

        df_trunc = None
        if sheet_trunc in xls.sheet_names:
            df_trunc = pd.read_excel(xls, sheet_trunc)

        df_other = None

        if sheet_other == "DRT Fit":
            drt_file = sibling_file(eis_file, "DRT")
            if drt_file.exists():
                drt_xls = pd.ExcelFile(_normalize_path(drt_file))
                if "Tknv_ReIm_s" in drt_xls.sheet_names:
                    df_other = pd.read_excel(drt_xls, "Tknv_ReIm_s")
        else:
            if sheet_other in xls.sheet_names:
                df_other = pd.read_excel(xls, sheet_other)

        if df_trunc is None:
            continue

        # --------------------------------------------------
        # Truncated vs Original
        # --------------------------------------------------
        if compare_mode == "Truncated vs Original":

            # Original FIRST (hollow circles)
            if df_other is not None:
                x = pd.to_numeric(df_other.iloc[:, 1], errors="coerce")
                y = -pd.to_numeric(df_other.iloc[:, 2], errors="coerce")

                ax.plot(
                    x, y,
                    linestyle='None',
                    marker='o',
                    markersize=6,
                    markerfacecolor='none',
                    markeredgecolor=color,
                    markeredgewidth=1.5,
                    alpha=0.5,
                    label=f"{label} - Original"
                )

                all_x.extend(x.dropna())
                all_y.extend(y.dropna())

            # Truncated SECOND (filled)
            x = pd.to_numeric(df_trunc.iloc[:, 1], errors="coerce")
            y = -pd.to_numeric(df_trunc.iloc[:, 2], errors="coerce")

            ax.plot(
                x, y,
                linestyle='None',
                marker='o',
                markersize=6,
                markerfacecolor=color,
                markeredgecolor=color,
                alpha=1.0,
                label=f"{label} - Truncated"
            )

            all_x.extend(x.dropna())
            all_y.extend(y.dropna())

        # --------------------------------------------------
        # X vs Truncated
        # --------------------------------------------------
        else:

            # Truncated (filled circles)
            x_tr = pd.to_numeric(df_trunc.iloc[:, 1], errors="coerce")
            y_tr = -pd.to_numeric(df_trunc.iloc[:, 2], errors="coerce")

            ax.plot(
                x_tr, y_tr,
                linestyle='None',
                marker='o',
                markersize=5,
                markerfacecolor=color,
                markeredgecolor=color,
                alpha=1.0
            )

            all_x.extend(x_tr.dropna())
            all_y.extend(y_tr.dropna())

            if df_other is not None:

                if sheet_other == "DRT Fit":
                    xcol = 2
                    ycol = 3
                else:
                    xcol = 1
                    ycol = 2

                x = pd.to_numeric(df_other.iloc[:, xcol], errors="coerce")
                y = -pd.to_numeric(df_other.iloc[:, ycol], errors="coerce")

                ax.plot(
                    x, y,
                    linewidth=1.8,
                    color=color,
                    alpha=0.9,
                    label=label  # Only filename
                )

                all_x.extend(x.dropna())
                all_y.extend(y.dropna())

    # --------------------------------------------------
    # Smart limits (same as add_nyquist_png)
    # --------------------------------------------------
    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)

        margin_x = (xmax - xmin) * 0.03
        margin_y = (ymax - ymin) * 0.03

        ax.set_xlim(xmin - margin_x, xmax + margin_x)

        if ymin < 0:
            ax.set_ylim(ymin - margin_y, ymax + margin_y)
        else:
            ax.set_ylim(0, ymax + margin_y)

    ax.set_xlabel("Z′ [Ω·cm²]")
    ax.set_ylabel("−Z″ [Ω·cm²]")

    ax.set_aspect('equal', adjustable='box')

    # Grid toggle
    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    # Legend toggle
    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )
        fig.subplots_adjust(right=0.75)

    # --------------------------------------------------
    # Export formats
    # --------------------------------------------------
    safe_name = compare_mode.replace(" ", "_").replace("→", "to")

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"Nyquist_Compare/{safe_name}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )

def add_drt_3d_png(zf: zipfile.ZipFile, datasets, title: str):

    fig = drt_3d_plotly(datasets, title)
    n_files = len(datasets)
    legend_font_size = max(10, min(16, int(22 - 0.8 * n_files)))

    fig.update_layout(
        template="plotly_white",
        title=None,

        font=dict(
            family="Arial",
            size=16,
            color="black"
        ),
        scene=dict(

            xaxis=dict(
                title=dict(
                    text="Frequency [Hz]",
                    font=dict(size=16, color="black")
                ),
                type="log",
                dtick=1,
                tickformat=".1g",        # clean numeric format
                exponentformat="power",  # 10^x style if needed
                tickangle=0,
                tickfont=dict(size=12, color="black"),

                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,

                showline=True,
                linecolor="black",
                linewidth=3,

                ticks="outside",
                autorange="reversed",
            ),

            yaxis=dict(
                title="",
                tickangle=0,
                tickfont=dict(size=12, color="black"),

                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,

                showline=True,
                linecolor="black",
                linewidth=3,

                ticks="outside",
            ),

            zaxis=dict(
                title=dict(
                    text="γ [Ω·cm²·s]",
                    font=dict(size=16, color="black")
                ),
                tickangle=0,
                tickfont=dict(size=12, color="black"),

                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,

                showline=True,
                linecolor="black",
                linewidth=3,

                ticks="outside",
            ),

            aspectmode="manual",
            aspectratio=dict(x=1.2, y=0.05*len(datasets), z=0.9),

            camera=dict(
                projection=dict(type="orthographic"),
                eye=dict(
                    x=-1.4,
                    y=1.4,
                    z=1.4
                )
            )

        ),

        legend=dict(
            orientation="v",
            y=0.5,
            yanchor="middle",
            x=1.02,
            xanchor="left",
            font=dict(size=legend_font_size, color="black"),
            bgcolor="rgba(255,255,255,0.9)"
        ),
        margin=dict(l=0, r=250, b=40, t=20)
    )

    if st.session_state.get("export_no_legend", False):

        fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=40, b=40, t=40)
        )

    else:

        fig.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=12, color="black"),
            ),
            margin=dict(l=40, r=220, b=40, t=40)
        )
    for fmt in st.session_state.export_formats:

        img_bytes = fig.to_image(
            format=fmt,
            scale=4,
            width=1600,
            height=1000
        )

        zf.writestr(f"DRT_3D/{title}_3D.{fmt}", img_bytes)

def add_nyquist_fit_png(zf: zipfile.ZipFile, datasets):

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    all_x = []
    all_y = []

    for i, (name, df) in enumerate(datasets):

        x = pd.to_numeric(df.iloc[:, 2], errors="coerce")
        y = -pd.to_numeric(df.iloc[:, 3], errors="coerce")

        if not st.session_state.get("export_no_nyquist_markers", False):
            ax.plot(
                x, y,
                linestyle='None',
                marker='o',
                markersize=3,
                markerfacecolor=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                markeredgecolor=COLOR_PALETTE[i % len(COLOR_PALETTE)],
                alpha=0.6
            )

        ax.plot(
            x, y,
            linewidth=1.5,
            color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
            alpha=0.85,
            label=latex_label(name)
        )

        all_x.extend(x.dropna())
        all_y.extend(y.dropna())

    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)

        margin_x = (xmax - xmin) * 0.03
        margin_y = (ymax - ymin) * 0.03

        ax.set_xlim(xmin - margin_x, xmax + margin_x)

        if ymin < 0:
            ax.set_ylim(ymin - margin_y, ymax + margin_y)
        else:
            ax.set_ylim(0, ymax + margin_y)

    ax.set_xlabel("Z′ [Ω·cm²]")
    ax.set_ylabel("−Z″ [Ω·cm²]")

    ax.set_aspect("equal", adjustable="box")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    if len(datasets) > 1 and not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"Nyquist/DRT_Fit.{fmt}",
            _fig_to_bytes(fig, fmt)
        )

def nyquist_fit_3d_plotly(datasets, title="Nyquist – DRT Smooth Fit (3D)"):
    """
    Nyquist-fit datasets use:
      Re  -> df.iloc[:, 2]
      Im  -> df.iloc[:, 3] (negated for -Z'')
    """
    fig = go.Figure()

    # ---- global ranges for equal scaling ----
    all_x = []
    all_z = []
    for _, df in datasets:
        x = pd.to_numeric(df.iloc[:, 2], errors="coerce").to_numpy()
        z = (-pd.to_numeric(df.iloc[:, 3], errors="coerce")).to_numpy()
        x = x[np.isfinite(x)]
        z = z[np.isfinite(z)]
        if len(x): all_x.append(x)
        if len(z): all_z.append(z)

    if all_x:
        all_x = np.concatenate(all_x)
        xmin, xmax = float(np.min(all_x)), float(np.max(all_x))
    else:
        xmin, xmax = 0.0, 1.0

    if all_z:
        all_z = np.concatenate(all_z)
        zmin, zmax = float(np.min(all_z)), float(np.max(all_z))
    else:
        zmin, zmax = 0.0, 1.0

    # ---- traces ----
    for i, (name, df) in enumerate(datasets):
        x = pd.to_numeric(df.iloc[:, 2], errors="coerce")
        z = -pd.to_numeric(df.iloc[:, 3], errors="coerce")
        y_spacing = 1.0
        y = np.full_like(x, i * y_spacing)

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        if not st.session_state.get("export_no_nyquist_markers", False):
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode="markers",
                marker=dict(size=3, color=color, opacity=0.6),
                showlegend=False
            ))
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode="lines",
            name=name,
            line=dict(color=color, width=4)
        ))
    x_range = max(xmax - xmin, 1e-12)
    z_range = max(zmax - zmin, 1e-12)    
    fig.update_layout(
        title=title,
        template="plotly_dark",
        scene=dict(
            xaxis=dict(title="Z′ [Ω·cm²]",autorange="reversed"),
            yaxis=dict(title="", showticklabels=False),
            zaxis=dict(title="−Z″ [Ω·cm²]"),
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=0.05*len(datasets),                     # arbitrary thin stacking axis
                z=z_range / x_range         # THIS enforces equal units
            ),

            camera=dict(
                eye=dict(
                    x=-1.7,
                    y=1.7,
                    z=1.7
                )
            )
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    return fig

def add_nyquist_fit_3d_png(zf: zipfile.ZipFile, datasets, title: str = "Nyquist_fit"):
    """
    Export Nyquist-fit as 3D PNG using the SAME white/scientific layout
    style as add_nyquist_3d_png, but with fit columns (Re col=2, Im col=3).
    """
    fig = nyquist_fit_3d_plotly(datasets, title)

    n_files = len(datasets)
    legend_font_size = max(10, min(16, int(22 - 0.8 * n_files)))
    all_x = []
    all_z = []

    for _, df in datasets:
        x = pd.to_numeric(df.iloc[:, 2], errors="coerce").to_numpy()
        z = (-pd.to_numeric(df.iloc[:, 3], errors="coerce")).to_numpy()

        x = x[np.isfinite(x)]
        z = z[np.isfinite(z)]

        if len(x):
            all_x.append(x)
        if len(z):
            all_z.append(z)

    if all_x:
        all_x = np.concatenate(all_x)
        xmin, xmax = float(np.min(all_x)), float(np.max(all_x))
    else:
        xmin, xmax = 0.0, 1.0

    if all_z:
        all_z = np.concatenate(all_z)
        zmin, zmax = float(np.min(all_z)), float(np.max(all_z))
    else:
        zmin, zmax = 0.0, 1.0
    x_range = max(xmax - xmin, 1e-12)
    z_range = max(zmax - zmin, 1e-12)    
    
    # ---- reuse same layout style as your other 3D Nyquist export ----
    fig.update_layout(
        template="plotly_white",
        title=None,

        font=dict(
            family="Arial",
            size=16,
            color="black"
        ),

        scene=dict(
            xaxis=dict(
                title=dict(text="Z′ [Ω·cm²]", font=dict(size=16, color="black")),
                tickfont=dict(size=12, color="black"),
                showgrid=not st.session_state.get("export_no_grid", False), gridcolor="lightgray", gridwidth=1,
                showline=True, linecolor="black", linewidth=3,
                ticks="outside",
                autorange="reversed",
            ),
            yaxis=dict(
                title="",
                showticklabels=False,
                showgrid=not st.session_state.get("export_no_grid", False), gridcolor="lightgray", gridwidth=1,
                showline=True, linecolor="black", linewidth=3,
                ticks="outside",
            ),
            zaxis=dict(
                title=dict(text="−Z″ [Ω·cm²]", font=dict(size=16, color="black")),
                tickfont=dict(size=12, color="black"),
                showgrid=not st.session_state.get("export_no_grid", False), gridcolor="lightgray", gridwidth=1,
                showline=True, linecolor="black", linewidth=3,
                ticks="outside",
            ),
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=0.05*len(datasets),                     # arbitrary thin stacking axis
                z=z_range / x_range         # THIS enforces equal units
            ),

            camera=dict(
                eye=dict(
                    x=-1.7,
                    y=1.7,
                    z=1.7
                )
            )
        ),

        legend=dict(
            orientation="v",
            y=0.5, yanchor="middle",
            x=1.02, xanchor="left",
            font=dict(size=legend_font_size, color="black"),
            bgcolor="rgba(255,255,255,0.9)"
        ),
        margin=dict(l=0, r=250, b=40, t=20)
    )
    if st.session_state.get("export_no_legend", False):

        fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=40, b=40, t=40)
        )

    else:

        fig.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=12, color="black"),
            ),
            margin=dict(l=40, r=220, b=40, t=40)
        )
    for fmt in st.session_state.export_formats:

        img_bytes = fig.to_image(
            format=fmt,
            scale=4,
            width=1600,
            height=1000
        )

        zf.writestr(f"Nyquist_3D/{title}_3D.{fmt}", img_bytes)
    
def add_nyquist_3d_png(zf: zipfile.ZipFile, datasets, title: str):

    fig = nyquist_3d_plotly(datasets, title)
    
    # --------------------------------------------------
    # 🔎 Compute TRUE global ranges for equal scaling
    # --------------------------------------------------
    all_x = []
    all_z = []

    for _, df in datasets:
        x = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy()
        z = (-pd.to_numeric(df.iloc[:, 2], errors="coerce")).to_numpy()

        x = x[np.isfinite(x)]
        z = z[np.isfinite(z)]

        if len(x):
            all_x.append(x)
        if len(z):
            all_z.append(z)

    if all_x:
        all_x = np.concatenate(all_x)
        xmin, xmax = float(np.min(all_x)), float(np.max(all_x))
    else:
        xmin, xmax = 0.0, 1.0

    if all_z:
        all_z = np.concatenate(all_z)
        zmin, zmax = float(np.min(all_z)), float(np.max(all_z))
    else:
        zmin, zmax = 0.0, 1.0
    x_range = max(xmax - xmin, 1e-12)
    z_range = max(zmax - zmin, 1e-12)    
    span = max(x_range, z_range)
    zoom_factor = span / 6
    # --------------------------------------------------
    # 🧪 Scientific white layout with TRUE equal scaling
    # --------------------------------------------------
    fig.update_layout(
        template="plotly_white",
        title=None,

        font=dict(
            family="Arial",
            size=16,
            color="black"
        ),

        scene=dict(
            
            xaxis=dict(
                title=dict(
                    text="Z′ [Ω·cm²]",
                    font=dict(size=16, color="black")
                ),
                tickangle=0,
                tickfont=dict(size=12, color="black"),
                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,
                showline=True,
                linecolor="black",
                linewidth=3,
                ticks="outside",
                autorange="reversed",
            ),

            yaxis=dict(
                title="",
                tickangle=0,
                tickfont=dict(size=12, color="black"),
                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,
                showline=True,
                linecolor="black",
                linewidth=3,
                ticks="outside",
            ),

            zaxis=dict(
                title=dict(
                    text="−Z″ [Ω·cm²]",
                    font=dict(size=16, color="black")
                ),
                tickangle=0,
                tickfont=dict(size=12, color="black"),
                showgrid=not st.session_state.get("export_no_grid", False),
                gridcolor="lightgray",
                gridwidth=1,
                showline=True,
                linecolor="black",
                linewidth=3,
                ticks="outside",
            ),

            # ✅ TRUE equal scaling between Z′ and Z″
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=0.05*len(datasets),                     # arbitrary thin stacking axis
                z=z_range / x_range         # THIS enforces equal units
            ),

            camera=dict(
                eye=dict(
                    x=-1.7,
                    y=1.7,
                    z=1.7
                )
            )
        ),

        legend=dict(
            orientation="v",
            y=1,
            yanchor="top",
            x=1.02,
            xanchor="left",
            font=dict(size=12, color="black"),
        ),
        margin=dict(l=40, r=220, b=40, t=40)
    )

    if st.session_state.get("export_no_legend", False):

        fig.update_layout(
            showlegend=False,
            margin=dict(l=40, r=40, b=40, t=40)
        )

    else:

        fig.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=12, color="black"),
            ),
            margin=dict(l=40, r=220, b=40, t=40)
        )

    for fmt in st.session_state.export_formats:

        img_bytes = fig.to_image(
            format=fmt,
            scale=4,
            width=1600,
            height=1000
        )

        zf.writestr(f"Nyquist_3D/{title}_3D.{fmt}", img_bytes)






def add_bode_png(zf: zipfile.ZipFile, datasets, title: str, real: bool):

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    all_x = []
    all_y = []

    for i, (name, df) in enumerate(datasets):

        freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")

        if real:
            y = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            ylabel = "Z′ [Ω·cm²]"
            subfolder = "Zreal"
        else:
            y = -pd.to_numeric(df.iloc[:, 2], errors="coerce")
            ylabel = "−Z″ [Ω·cm²]"
            subfolder = "Zimag"

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        # --- markers (raw style)
        if not st.session_state.get("export_no_nyquist_markers", False):
            ax.semilogx(
                freq, y,
                linestyle='None',
                marker='o',
                markersize=3,
                markerfacecolor=color,
                markeredgecolor=color,
                alpha=0.6
            )

        # --- smooth connecting line
        ax.semilogx(
            freq, y,
            linewidth=1.5,
            color=color,
            alpha=0.85,
            label=latex_label(name)
        )

        all_x.extend(freq.dropna())
        all_y.extend(y.dropna())

    # ---- Smart limits ----
    if all_x and all_y:

        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)

        margin_y = (ymax - ymin) * 0.03 if ymax != ymin else 0.05 * ymax

        ax.set_xlim(xmin, xmax)

        if ymin < 0:
            ax.set_ylim(ymin - margin_y, ymax + margin_y)
        else:
            ax.set_ylim(0, ymax + margin_y)

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel(ylabel)

    # Nature-style grid
    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    # ---- Legend BELOW ----
    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )
        fig.subplots_adjust(right=0.75)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"Bode/{subfolder}/{title}_{subfolder}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )
   


def add_drt_png(zf: zipfile.ZipFile, datasets, title: str):

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    all_freq = []
    ymax = 0

    for i, (name, df) in enumerate(datasets):

        freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
        gamma = pd.to_numeric(df.iloc[:, 1], errors="coerce")

        ax.semilogx(
            freq,
            gamma,
            linewidth=1.5,
            alpha=0.85,
            color=COLOR_PALETTE[i % len(COLOR_PALETTE)],
            label=latex_label(name),
        )

        all_freq.extend(freq.dropna())

        gamma_valid = gamma[np.isfinite(gamma)]
        if len(gamma_valid):
            ymax = max(ymax, gamma_valid.max())

    # ---- Smart limits ----
    if all_freq:
        ax.set_xlim(min(all_freq), max(all_freq))

    ax.set_ylim(0, 1.05 * ymax if ymax > 0 else 1)

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("γ [Ω·cm²·s]")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    # ---- Legend BELOW ----
    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False
        )
        fig.subplots_adjust(right=0.75)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"DRT/{title}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )



def add_cnls_bar_png(zf: zipfile.ZipFile, series: pd.Series, fname: str):

    # Detect dynamic Rn keys
    r_keys = sorted(
        [k for k in series.index if k.startswith("R") and k != "R_ohmic"],
        key=lambda x: int(x[1:])
    )

    r_keys = list(reversed(r_keys))
    order_keys = ["ASR", "R_ohmic"] + r_keys

    # Extract values using TRUE keys
    y = [series.get(k, np.nan) for k in order_keys]

    # Create display labels (LaTeX only for R_ohmic)
    display_labels = []
    for k in order_keys:
        if k == "R_ohmic":
            display_labels.append(r"$R_{\mathrm{ohmic}}$")
        else:
            display_labels.append(k)

    fig, ax = plt.subplots(figsize=(7, 4), dpi=300)

    ax.bar(display_labels, y)

    ax.set_yscale("log")
    ax.set_ylabel("R [Ω·cm²]")

    ax.grid(False)
    ax.tick_params(axis="x", rotation=30)
    
    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"CNLS/{fname}_bar.{fmt}",
            _fig_to_bytes(fig, fmt)
        )

def add_cnls_line_png(zf: zipfile.ZipFile, df_cnls: pd.DataFrame, param: str):

    x = np.arange(1, len(df_cnls) + 1)
    y = df_cnls[param].values
    x_labels = [str(idx) for idx in df_cnls.index.tolist()]

    mean_val = np.nanmean(y)
    std_val = np.nanstd(y)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    # ---- White main line (no legend) ----
    ax.plot(
        x,
        y,
        linewidth=1.5,
        color="black"
    )

    # ---- Colored hollow markers + legend ----
    legend_handles = []

    for i, (idx, val) in enumerate(zip(df_cnls.index.tolist(), y)):

        color = COLOR_PALETTE[i % len(COLOR_PALETTE)]

        sc = ax.scatter(
            i+1,
            val,
            facecolors="white",
            edgecolors=color,
            s=80,
            linewidth=2
        )

        legend_handles.append(
            plt.Line2D(
                [0], [0],
                marker='o',
                color='white',
                markeredgecolor=color,
                markerfacecolor='white',
                markersize=8,
                linewidth=0,
                label=f"{i+1} - {latex_label(idx)}"
            )
        )

    ax.set_xlabel("File index")
    ax.set_ylabel("R [Ω·cm²]")
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30, ha="right")

    ax.set_title(
        f"Mean value: {mean_val:.3g} | Std value: {std_val:.3g}"
    )

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    n = len(legend_handles)
    legend_font = max(6, min(10, int(12 - 0.25 * n)))

    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            handles=legend_handles,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=False,
            fontsize=legend_font
        )
        fig.subplots_adjust(right=0.78)
    
    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"CNLS/LinePlots/{param}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )
   
def add_cnls_elements_fitting_png(
    zf: zipfile.ZipFile,
    cnls_file: Path,
    fname: str
):

    if not cnls_file.exists():
        return

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "DRT" not in xls.sheet_names or "Summary" not in xls.sheet_names:
        return

    # ---- Detect RQ elements from Summary ----
    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))

    df = pd.read_excel(xls, "DRT")

    if df.shape[1] < 6:
        return

    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    gamma_total = pd.to_numeric(df.iloc[:, 1], errors="coerce")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    # ---- TOTAL γ (main DRT) ----
    ax.semilogx(
        freq,
        gamma_total,
        linewidth=1.5,
        color="black",
        alpha=0.3,
        label="Total γ"
    )

    ymax = np.nanmax(gamma_total)
    # Generate enough distinct colors for all RQ elements
    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=len(rq_elements)
    )
    # ---- Individual RQ contributions ----
    for i, rq in enumerate(rq_elements):

        gamma_elem = pd.to_numeric(
            df.iloc[:, 5 + i],
            errors="coerce"
        )

        ax.semilogx(
            freq,
            gamma_elem,
            linewidth=1.5,
            color=element_colors[i],
            label=rq
        )

        elem_max = np.nanmax(gamma_elem)
        if np.isfinite(elem_max):
            ymax = max(ymax, elem_max)

    # ---- Scientific limits ----
    ax.set_xlim(np.nanmin(freq), np.nanmax(freq))
    ax.set_ylim(0, 1.05 * ymax)

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("γ [Ω·cm²·s]")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    # ---- Legend BELOW (consistent with others) ----
    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            ncol=1,
            frameon=False
        )
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"CNLS/Fitting/{fname}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )
 

def add_cnls_nyquist_fit_png(zf, cnls_file, fname):

    fig, ax = plt.subplots(figsize=(6, 6), dpi=600)

    xls = pd.ExcelFile(_normalize_path(cnls_file))
    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))

    df = pd.read_excel(xls, "Z")

    # ---- Main Nyquist ----
    z_real_total = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    z_imag_total = -pd.to_numeric(df.iloc[:, 2], errors="coerce")

    ax.plot(
        z_real_total,
        z_imag_total,
        linewidth=1.5,
        color="black",
        alpha=0.3,
        label="Total Z"
    )

    # ---- Ohmic real column
    z_ohmic = pd.to_numeric(df.iloc[:, 11], errors="coerce")
    offset = z_ohmic.iloc[-1]

    start_col = 13

    # Generate enough distinct colors for all RQ elements
    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=len(rq_elements)
    )

    for i, rq in enumerate(rq_elements):

        real_col = start_col + 2*i
        imag_col = start_col + 2*i + 1

        if imag_col >= df.shape[1]:
            break

        z_r = pd.to_numeric(df.iloc[:, real_col], errors="coerce")
        z_i = -pd.to_numeric(df.iloc[:, imag_col], errors="coerce")

        shifted_real = z_r + offset

        ax.plot(
            shifted_real,
            z_i,
            linewidth=1.5,
            color=element_colors[i],
            label=rq
        )

        offset += z_r.iloc[-1]

    ax.set_xlabel("Z′ [Ω·cm²]")
    ax.set_ylabel("−Z″ [Ω·cm²]")
    ax.set_aspect("equal", adjustable="box")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            ncol=1,
            frameon=False
        )
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"CNLS/Fitting/Nyquist_{fname}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )

def add_cnls_residuals_png(zf, cnls_file, fname):

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    xls = pd.ExcelFile(_normalize_path(cnls_file))
    df = pd.read_excel(xls, "Z")

    freq = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    res_real = 100 * pd.to_numeric(df.iloc[:, 7], errors="coerce")
    res_imag = 100 * pd.to_numeric(df.iloc[:, 8], errors="coerce")

    if st.session_state.get("export_no_nyquist_markers", False):

        ax.semilogx(
            freq, res_real,
            linewidth=1.2,
            color=COLOR_PALETTE[0],
            label="Real"
        )

        ax.semilogx(
            freq, res_imag,
            linewidth=1.2,
            color=COLOR_PALETTE[1],
            label="Imaginary"
        )

    else:

        ax.semilogx(
            freq, res_real,
            marker='o',
            markersize=4,
            linewidth=1.2,
            color=COLOR_PALETTE[0],
            label="Real"
        )

        ax.semilogx(
            freq, res_imag,
            marker='o',
            markersize=4,
            linewidth=1.2,
            color=COLOR_PALETTE[1],
            label="Imaginary"
        )

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Residual [%]")

    if st.session_state.get("export_no_grid", False):
        ax.grid(False)
    else:
        ax.grid(True, linewidth=0.5, alpha=0.3)

    if not st.session_state.get("export_no_legend", False):
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            ncol=1,
            frameon=False
        )
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(
            f"CNLS/Fitting/Res_{fname}.{fmt}",
            _fig_to_bytes(fig, fmt)
        )


def add_cnls_compare_png(zf: zipfile.ZipFile, cnls_file: Path, fname: str):
    """Export all three CNLS compare plots (imaginary Bode, Nyquist, DRT) to CNLS/Compare/."""

    if not cnls_file.exists():
        return

    xls = pd.ExcelFile(_normalize_path(cnls_file))

    if "Z" not in xls.sheet_names or "Summary" not in xls.sheet_names:
        return

    summary_df = pd.read_excel(xls, "Summary", header=None)
    elements_raw = summary_df.iloc[1, 0]
    rq_elements = re.findall(r"RQ\d+", str(elements_raw))
    element_colors = sample_palette_colors(
        st.session_state.palette_choice,
        n=max(1, len(rq_elements))
    )

    df_z = pd.read_excel(xls, "Z")
    freq = pd.to_numeric(df_z.iloc[:, 0], errors="coerce")

    # ---- 1. Imaginary Bode ----
    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)

    zmes_im = -pd.to_numeric(df_z.iloc[:, 2], errors="coerce")
    marker_kw = {} if st.session_state.get("export_no_nyquist_markers", False) else dict(marker='o', markersize=3)
    ax.semilogx(freq, zmes_im, linewidth=1.0, color="black", label="Measure", **marker_kw)

    rq_im_map = {}
    for col in df_z.columns:
        m = re.match(r"(RQ\d+)_Im", col)
        if m:
            rq_im_map[m.group(1)] = col

    for i, rq in enumerate(rq_elements):
        if rq not in rq_im_map:
            continue
        z_im = -pd.to_numeric(df_z[rq_im_map[rq]], errors="coerce")
        ax.semilogx(freq, z_im, linewidth=1.5, color=element_colors[i], label=rq)

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("−Z″ [Ω·cm²]")

    if not st.session_state.get("export_no_grid", False):
        ax.grid(True, linewidth=0.5, alpha=0.3)
    if not st.session_state.get("export_no_legend", False):
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), ncol=1, frameon=False)
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(f"CNLS/Compare/{fname}_im_bode.{fmt}", _fig_to_bytes(fig, fmt))

    # ---- 2. Nyquist with individual element arcs ----
    fig, ax = plt.subplots(figsize=(6, 6), dpi=600)

    z_real_total = pd.to_numeric(df_z.iloc[:, 1], errors="coerce")
    z_imag_total = -pd.to_numeric(df_z.iloc[:, 2], errors="coerce")
    ax.plot(z_real_total, z_imag_total, linewidth=1.5, color="black", alpha=0.3, label="Total Z")

    z_ohmic = pd.to_numeric(df_z.iloc[:, 11], errors="coerce")
    offset = z_ohmic.iloc[-1]
    start_col = 13

    for i, rq in enumerate(rq_elements):
        real_col = start_col + 2 * i
        imag_col = start_col + 2 * i + 1
        if imag_col >= df_z.shape[1]:
            break
        z_r = pd.to_numeric(df_z.iloc[:, real_col], errors="coerce")
        z_i = -pd.to_numeric(df_z.iloc[:, imag_col], errors="coerce")
        ax.plot(z_r + offset, z_i, linewidth=1.5, color=element_colors[i], label=rq)
        offset += z_r.iloc[-1]

    ax.set_xlabel("Z′ [Ω·cm²]")
    ax.set_ylabel("−Z″ [Ω·cm²]")
    ax.set_aspect("equal", adjustable="box")

    if not st.session_state.get("export_no_grid", False):
        ax.grid(True, linewidth=0.5, alpha=0.3)
    if not st.session_state.get("export_no_legend", False):
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), ncol=1, frameon=False)
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(f"CNLS/Compare/{fname}_nyquist.{fmt}", _fig_to_bytes(fig, fmt))

    # ---- 3. DRT with individual element contributions ----
    if "DRT" not in xls.sheet_names:
        return

    df_drt = pd.read_excel(xls, "DRT")
    if df_drt.shape[1] < 6:
        return

    freq_drt = pd.to_numeric(df_drt.iloc[:, 0], errors="coerce")
    gamma_total = pd.to_numeric(df_drt.iloc[:, 1], errors="coerce")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=600)
    ax.semilogx(freq_drt, gamma_total, linewidth=1.5, color="black", alpha=0.3, label="Total γ")

    ymax = float(np.nanmax(gamma_total))
    for i, rq in enumerate(rq_elements):
        if 5 + i >= df_drt.shape[1]:
            break
        gamma_elem = pd.to_numeric(df_drt.iloc[:, 5 + i], errors="coerce")
        ax.semilogx(freq_drt, gamma_elem, linewidth=1.5, color=element_colors[i], label=rq)
        elem_max = float(np.nanmax(gamma_elem))
        if np.isfinite(elem_max):
            ymax = max(ymax, elem_max)

    ax.set_xlim(float(np.nanmin(freq_drt)), float(np.nanmax(freq_drt)))
    ax.set_ylim(0, 1.05 * ymax)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("γ [Ω·cm²·s]")

    if not st.session_state.get("export_no_grid", False):
        ax.grid(True, linewidth=0.5, alpha=0.3)
    if not st.session_state.get("export_no_legend", False):
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), ncol=1, frameon=False)
        fig.subplots_adjust(right=0.78)

    for fmt in st.session_state.export_formats:
        zf.writestr(f"CNLS/Compare/{fname}_drt.{fmt}", _fig_to_bytes(fig, fmt))


def add_cnls_heatmap_png(zf: zipfile.ZipFile, df_cnls: pd.DataFrame, palette_choice: str, param_groups=None):

    if param_groups is None:
        param_groups = ["R", "Time constant", "Alpha"]

    cmap_name = PALETTE_LIBRARY.get(palette_choice, "viridis") if palette_choice in PLOTLY_SEQ else "viridis"
    y_labels = [latex_label(i) for i in df_cnls.index.tolist()]
    r_indices = sorted(
        {int(k[1:]) for k in df_cnls.columns if k.startswith("R") and k != "R_ohmic"}
    )
    no_grid = st.session_state.get("export_no_grid", False)

    def _write_heatmap(data_arr, x_labels, cbar_label, zip_name, vmin=None, vmax=None):
        n_rows, n_cols = data_arr.shape
        fig, ax = plt.subplots(figsize=(1.2 * n_cols, max(3, 0.6 * n_rows)), dpi=600)
        im = ax.imshow(
            data_arr, aspect="auto", cmap=cmap_name,
            vmin=vmin if vmin is not None else np.nanmin(data_arr),
            vmax=vmax if vmax is not None else np.nanmax(data_arr),
        )
        ax.set_xticks(np.arange(n_cols))
        ax.set_xticklabels(x_labels, rotation=30, ha="right")
        ax.set_yticks(np.arange(n_rows))
        ax.set_yticklabels(y_labels)
        ax.set_xticks(np.arange(-.5, n_cols, 1), minor=True)
        ax.set_yticks(np.arange(-.5, n_rows, 1), minor=True)
        if not no_grid:
            ax.grid(which="minor", color="white", linestyle="-", linewidth=1.2)
        ax.tick_params(which="minor", bottom=False, left=False)
        fig.colorbar(im, ax=ax).set_label(cbar_label)
        fig.tight_layout()
        for fmt in st.session_state.export_formats:
            zf.writestr(f"CNLS/{zip_name}.{fmt}", _fig_to_bytes(fig, fmt))

    # ---- Resistances (log scale) ----
    if "R" in param_groups:
        r_cols = [f"R{i}" for i in r_indices if f"R{i}" in df_cnls.columns]
        r_col_order = [c for c in ["ASR", "R_ohmic"] + r_cols if c in df_cnls.columns]
        if r_col_order:
            data = df_cnls[r_col_order].values.astype(float)
            data[data <= 0] = np.nan
            x_labels = [r"$R_{\mathrm{ohmic}}$" if c == "R_ohmic" else c for c in r_col_order]
            _write_heatmap(np.log10(data), x_labels, "log(R [Ω·cm²])", "CNLS_heatmap_R")

    # ---- Time constants (log scale) ----
    if "Time constant" in param_groups:
        tau_cols = [f"tau{i}" for i in r_indices if f"tau{i}" in df_cnls.columns]
        if tau_cols:
            data = df_cnls[tau_cols].values.astype(float)
            data[data <= 0] = np.nan
            x_labels = [fr"$\tau_{{{c[3:]}}}$" for c in tau_cols]
            _write_heatmap(np.log10(data), x_labels, "log(τ [s])", "CNLS_heatmap_tau")

    # ---- Dispersion factors (linear 0–1) ----
    if "Alpha" in param_groups:
        alpha_cols = [f"alpha{i}" for i in r_indices if f"alpha{i}" in df_cnls.columns]
        if alpha_cols:
            data = df_cnls[alpha_cols].values.astype(float)
            x_labels = [fr"$\alpha_{{{c[5:]}}}$" for c in alpha_cols]
            _write_heatmap(data, x_labels, "α", "CNLS_heatmap_alpha", vmin=0, vmax=1)



# ===============================
# App
# ===============================
st.set_page_config(page_title="SOCEIS Data Viewer", layout="wide")
st.title("SOCEIS Data Viewer")

with st.sidebar:
    # --- Root folder input + browse button (manual typing preserved) ---
    if "root_input" not in st.session_state:
        st.session_state.root_input = str(DEFAULT_ROOT_FOLDER)

    col_left, col_right = st.columns([0.82, 0.18], vertical_alignment="bottom")

    with col_left:
        st.session_state.root_input = st.text_input(
            "Root folder (auto-discover EIS)",
            value=st.session_state.root_input
        )

    with col_right:
        browse = st.button("📁", width='stretch')

    if browse:
        selected_folder = pick_folder_dialog(
            current_dir=st.session_state.root_input,
            fallback_dir=DEFAULT_ROOT_FOLDER,
        )
        if selected_folder:
            st.session_state.root_input = selected_folder
            st.rerun()
        else:
            if not TK_AVAILABLE:
                st.warning("Folder picker unavailable. On macOS, please allow Terminal/Python automation access to Finder, or type the path manually.")
            # If user canceled dialog, do nothing.

    root_path = Path(st.session_state.root_input)

    # Detect root folder change so the export path can follow it
    _root_changed = st.session_state.get("_last_root_input") != st.session_state.root_input
    st.session_state["_last_root_input"] = st.session_state.root_input

    eis_files = discover_eis_files(root_path) if root_path.exists() else []
    if not eis_files:
        st.warning("No EIS folders/files found under the given root.")
        st.stop()

    display_map = {str(f.relative_to(root_path)): f for f in eis_files}
    

   # ---- init palette choice BEFORE any read ----
    if "palette_choice" not in st.session_state:
        st.session_state.palette_choice = "Default"

    PALETTE_PREVIEW_N = 10  # keep preview squares fixed

    # ---- Initialize state ----
    if "selected_files" not in st.session_state:
        st.session_state.selected_files = []

    st.markdown("### Select EIS files")

    col_left, col_right = st.columns([0.88, 0.12], vertical_alignment="bottom")

    # ---- Button FIRST ----
    with col_right:
        if st.button("All", width='stretch'):
            st.session_state.selected_files = list(display_map.keys())

    # ---- Then create the widget ----
    with col_left:
        selected = st.multiselect(
            " ",
            options=list(display_map.keys()),
            key="selected_files"
        )
    # ---- Optional alphabetical ordering ----
    sort_mode = st.selectbox(
        "File ordering",
        [
            "Original selection order",
            "Alphabetical by filename (A → Z)",
            "Alphabetical by filename (Z → A)",
            "Alphabetical by full path (A → Z)",
            "Alphabetical by full path (Z → A)"
        ],
        index=1
    )
    show_legend_table = st.checkbox(
        "Show personalized legend table",
        value=True,
        key="show_legend_table"
    )

    selected_keys = st.session_state.selected_files

    if sort_mode == "Alphabetical by filename (A → Z)":
        selected_keys = sorted(
            selected_keys,
            key=lambda k: natural_key(Path(k).name)
        )

    elif sort_mode == "Alphabetical by filename (Z → A)":
        selected_keys = sorted(
            selected_keys,
            key=lambda k: natural_key(Path(k).name),
            reverse=True
        )

    elif sort_mode == "Alphabetical by full path (A → Z)":
        selected_keys = sorted(
            selected_keys,
            key=lambda k: natural_key(k)
        )

    elif sort_mode == "Alphabetical by full path (Z → A)":
        selected_keys = sorted(
            selected_keys,
            key=lambda k: natural_key(k),
            reverse=True
        )

# else: Original selection order → do nothing
# else: keep original selection order

    files_to_process = [display_map[s] for s in selected_keys]
    # --- Always initialize custom_names once ---
    if "custom_names" not in st.session_state:
        st.session_state["custom_names"] = {}

    # Ensure every selected file has a default label
    for f in files_to_process:
        st.session_state["custom_names"].setdefault(f.name, f.stem)

    n_files = max(2, len(files_to_process))
    st.markdown("### Colors")

    # (2) Palette selector (single widget with one key)
    st.selectbox(
        "Color palette",
        options=list(PALETTE_LIBRARY.keys()),
        key="palette_choice",
    )

    # (3) Actual colors used in plots (adapts to number of selected files)
    COLOR_PALETTE = sample_palette_colors(st.session_state.palette_choice, n=n_files)

    # (4) Preview (fixed number of squares, but correct palette range)
    preview_colors = sample_palette_colors(st.session_state.palette_choice, n=PALETTE_PREVIEW_N)
    st.markdown(render_palette_preview(preview_colors), unsafe_allow_html=True)
    

    st.header("Nyquist")
    # Build Nyquist options dynamically
    NYQUIST_TYPES_DYNAMIC = list(NYQUIST_TYPES)  # Original, Truncated, etc.
    drt_fit_available = has_drt_fit(files_to_process)
    if drt_fit_available:
        NYQUIST_TYPES_DYNAMIC.append("DRT Fit")
    # If "DRT Fit" was selected previously but now not available, remove it
    prev = st.session_state.get("nyquist_selected", [])
    if (not drt_fit_available) and ("DRT Fit" in prev):
        st.session_state["nyquist_selected"] = [x for x in prev if x != "DRT Fit"]
    nyquist_selected = st.multiselect(
        "Nyquist types",
        NYQUIST_TYPES_DYNAMIC,
        default=[x for x in DEFAULT_NYQUIST if x in NYQUIST_TYPES_DYNAMIC],
        key="nyquist_selected"
    )
    # -------------------------
    # Nyquist Compare
    # -------------------------

    compare_options = [
        "Truncated vs Original",
        "Smooth vs Truncated",
        "LC corrected vs Truncated",
        "Extended vs Truncated"
    ]

    if drt_fit_available:
        compare_options.append("DRT Fit vs Truncated")

    nyquist_compare_selected = st.multiselect(
        "Compare",
        compare_options,
        default=["Smooth vs Truncated"]
    )

    nyquist_show_params = st.checkbox("Parameters", value=False, key="nyq_params")

    st.header("Bode")
    bode_selected = st.multiselect("Bode types", BODE_TYPES, default=[])
    zhit_show = st.checkbox("Z-HIT", value=False, key="zhit_show")

    st.header("DRT")
    drt_selected = st.multiselect("DRT types", DRT_TYPES, default=["Truncated"])
    drt_show_params = st.checkbox("Parameters", value=False, key="drt_params")


    st.header("CNLS")

    if len(selected) == 1:
        # Single file
        cnls_plot_modes = st.multiselect(
            "CNLS plot types",
            ["Bar plot", "Elements fitting", "CNLS compare"],
            default=[]
        )
        cnls_line_selection = []
        cnls_heatmap_params = []
    else:
        # Multiple files
        cnls_plot_modes = st.multiselect(
            "CNLS plot types",
            ["Heatmap", "Line plots", "CNLS compare"],
            default=[]
        )
        cnls_line_selection = []
        cnls_heatmap_params = (
            st.multiselect(
                "Heatmap parameters",
                ["R", "Time constant", "Alpha"],
                default=["R", "Time constant", "Alpha"],
                key="cnls_heatmap_params"
            )
            if "Heatmap" in cnls_plot_modes
            else []
        )

    cnls_show_params = st.checkbox("Parameters", value=False, key="cnls_params")
    analyze_cnls = bool(cnls_plot_modes) or cnls_show_params

    st.header("3D Visualization")
    nyquist_3d = st.checkbox("3D Nyquist", value=False)
    drt_3d = st.checkbox("3D DRT", value=False)

    st.header("Export")
    export_no_nyquist_markers = st.checkbox(
        "Remove markers",
        value=False,
        key="export_no_nyquist_markers"
    )

    export_no_grid = st.checkbox(
        "Remove grid lines",
        value=False,
        key="export_no_grid"
    )

    export_no_legend = st.checkbox(
        "Remove legends",
        value=False,
        key="export_no_legend"
    )

    if "export_input" not in st.session_state or _root_changed:
        st.session_state.export_input = str(Path(st.session_state.root_input) / "SOCEIS_figures")

    col_left, col_right = st.columns([0.82, 0.18], vertical_alignment="bottom")

    with col_left:
        st.session_state.export_input = st.text_input(
            "Export folder path",
            value=st.session_state.export_input
        )

    with col_right:
        browse_export = st.button("📁", key="browse_export", width='stretch')

    if browse_export:
        selected_folder = pick_folder_dialog(
            current_dir=st.session_state.export_input,
            fallback_dir=DEFAULT_EXPORT_FOLDER,
        )
        if selected_folder:
            st.session_state.export_input = selected_folder
            st.rerun()

    export_folder = Path(st.session_state.export_input)
    # ------------------------------
    # Export file types
    # ------------------------------

    export_formats = st.multiselect(
        "Select formats",
        options=["png", "jpg", "pdf"],
        default=["png"],
        key="export_formats"
    )

    # Safety fallback
    if not export_formats:
        st.session_state.export_formats = ["png"]
    save_zip = st.button("💾 Save ZIP")
    # --- Export styling toggles ---

if not files_to_process:
    st.info("Select at least one EIS file.")
    st.stop()

# --- Always build display_name_map (even if legend table is hidden) ---
if show_legend_table:
    display_name_map = {
        f.name: st.session_state["custom_names"].get(f.name, f.stem)
        for f in files_to_process
    }
else:
    # fallback to filename without extension
    display_name_map = {f.name: f.stem for f in files_to_process}


# ===============================
# File Label Editor (Main Page)
# ===============================
if show_legend_table:
    st.subheader("Selected Files")

    # Build current table from session_state (source of truth)
    rows = []
    for idx, f in enumerate(files_to_process, start=1):
        fname = f.name
        rows.append({
            "Index": idx,
            "File name": fname,
            "Personalized name (LaTeX-friendly)": st.session_state.custom_names.get(fname, Path(fname).stem),
        })

    df_labels = pd.DataFrame(rows)

    # ---- EDITOR INSIDE A FORM (only commits on Apply) ----
    with st.form("legend_editor_form", clear_on_submit=False):
        edited_df = st.data_editor(
            df_labels,
            key="legend_editor",  # IMPORTANT: stable key
            column_config={
                "Index": st.column_config.NumberColumn(disabled=True),
                "File name": st.column_config.TextColumn(disabled=True),
                "Personalized name (LaTeX-friendly)": st.column_config.TextColumn(),
            },
            hide_index=True,
            width='stretch',
        )

        colA, colB = st.columns([0.25, 0.75])
        with colA:
            apply_labels = st.form_submit_button("✅ Apply labels")

        # Optional: reset inside the form
        with colB:
            reset_labels = st.form_submit_button("↩ Reset to filenames")

    # ---- APPLY / RESET (only here, after button press) ----
    if apply_labels:
        for _, row in edited_df.iterrows():
            st.session_state.custom_names[row["File name"]] = row["Personalized name (LaTeX-friendly)"]
        st.rerun()

    if reset_labels:
        for f in files_to_process:
            st.session_state.custom_names[f.name] = f.stem
        st.rerun()

# ===============================
# Load data
# ===============================
eis_param_rows: List[Dict] = []
drt_param_rows: List[Dict] = []
cnls_rows: List[Dict] = []

nyquist_data: Dict[str, List[Tuple[str, pd.DataFrame]]] = {p: [] for p in nyquist_selected}
bode_data: Dict[str, List[Tuple[str, pd.DataFrame]]] = {p: [] for p in bode_selected}
drt_data: Dict[str, List[Tuple[str, pd.DataFrame]]] = {p: [] for p in drt_selected}
zhit_data: List[Tuple[str, pd.DataFrame]] = []

for eis_file in files_to_process:
    fname = eis_file.name
    xls = pd.ExcelFile(_normalize_path(eis_file))

    # EIS parameters
    eis_param_rows.append(extract_eis_parameters(xls, fname))

    # Nyquist
    for p in nyquist_selected:
        if p in xls.sheet_names:
            df = pd.read_excel(xls, p)
            if df.shape[1] >= 3:
                label = display_name_map.get(fname, fname)
                nyquist_data[p].append((latex_label(label), df))

    # Bode 
    for p in bode_selected:
        if p in xls.sheet_names:
            df = pd.read_excel(xls, p)
            if df.shape[1] >= 3:
                label = display_name_map.get(fname, fname)
                bode_data[p].append((latex_label(label), df))

    # Z-HIT
    if zhit_show and "ZHIT" in xls.sheet_names:
        df_zhit = pd.read_excel(xls, "ZHIT")
        if df_zhit.shape[1] >= 6:
            label = display_name_map.get(fname, fname)
            zhit_data.append((latex_label(label), df_zhit))

    # DRT from sibling DRT file
    drt_file = sibling_file(eis_file, "DRT")
    if drt_file.exists():
        drt_xls = pd.ExcelFile(_normalize_path(drt_file))

        lam_row = extract_drt_lambda(drt_xls, fname)
        if lam_row is not None:
            drt_param_rows.append(lam_row)

        for p in drt_selected:
            sheet = DRT_SHEET_MAP[p]
            if sheet in drt_xls.sheet_names:
                df = pd.read_excel(drt_xls, sheet)
                if df.shape[1] >= 2:
                    label = display_name_map.get(fname, fname)
                    drt_data[p].append((latex_label(label), df))

        # ---- Nyquist "DRT Fit" (from DRT file) ----
        if "DRT Fit" in nyquist_selected:
            if "Tknv_ReIm_s" in drt_xls.sheet_names:
                df_fit = pd.read_excel(drt_xls, "Tknv_ReIm_s")
                if df_fit.shape[1] >= 4:
                    label = display_name_map.get(fname, fname)
                    nyquist_data.setdefault("DRT Fit", [])
                    nyquist_data["DRT Fit"].append((latex_label(label), df_fit))

    # CNLS from sibling CNLS file (optional)
        if analyze_cnls:
            cnls_file = sibling_file(eis_file, "CNLS")
            params = extract_cnls_parameters(cnls_file)
            if params is not None:
                display_label = display_name_map.get(fname, fname)
                params_row = {"File": display_label, **params}
                cnls_rows.append(params_row)


# ===============================
# Plot display
# ===============================
if nyquist_show_params:
    st.subheader("Nyquist")
    eis_cols = ["File"] + [lbl for (lbl, _) in EIS_PARAM_ORDER]
    df_eis_params = pd.DataFrame(eis_param_rows).reindex(columns=eis_cols)
    df_eis_params.index = np.arange(1, len(df_eis_params) + 1)
    df_eis_params.index.name = "Index"
    st.dataframe(df_eis_params, width="stretch")

if nyquist_selected:
    if not nyquist_show_params:
        st.subheader("Nyquist")
    
    for p, data in nyquist_data.items():
        if not data:
            continue

        if nyquist_3d:
            if p == "DRT Fit":
                st.plotly_chart(
                    nyquist_3d_plotly_cols(data, "Nyquist - DRT Fit", x_col=2, y_col=3, negate_y=True),
                    width="stretch"
                )
            else:
                st.plotly_chart(nyquist_3d_plotly(data, p), width="stretch")
        else:
            if p == "DRT Fit":
                st.plotly_chart(nyquist_fit_plotly(data), width="stretch")
            else:
                st.plotly_chart(nyquist_plotly(data, p), width="stretch")

# ===============================
# Nyquist Compare Plots
# ===============================

if nyquist_compare_selected:

    if not nyquist_show_params and not nyquist_selected:
        st.subheader("Nyquist")

    for mode in nyquist_compare_selected:
        fig = nyquist_compare_plotly(
            mode,
            files_to_process,
            display_name_map
        )
        st.plotly_chart(fig, width="stretch")

if bode_selected:
    st.subheader("Bode")

    for p, data in bode_data.items():
        if data:
            # One title per Bode type
            st.markdown(f"**{p}**")

            # Real part
            st.plotly_chart(
                bode_plotly(data, p, real=True),
                width="stretch",
                key=f"bode_{p}_real"
            )

            # Imaginary part
            st.plotly_chart(
                bode_plotly(data, p, real=False),
                width="stretch",
                key=f"bode_{p}_imag"
            )

if zhit_show and zhit_data:
    st.subheader("Z-HIT")
    st.plotly_chart(zhit_plotly(zhit_data, mode="modulus"), width="stretch", key="zhit_modulus")
    st.plotly_chart(zhit_plotly(zhit_data, mode="phase"),   width="stretch", key="zhit_phase")
    st.plotly_chart(zhit_plotly(zhit_data, mode="delta"),   width="stretch", key="zhit_delta")

if drt_show_params and drt_param_rows:
    st.subheader("DRT")
    df_drt_params = pd.DataFrame(drt_param_rows)
    df_drt_params.index = np.arange(1, len(df_drt_params) + 1)
    df_drt_params.index.name = "Index"
    st.data_editor(
        df_drt_params,
        column_config={
            "tknv_pos": st.column_config.CheckboxColumn(
                "Tikhonov positive definite",
                help="True if positivity constraint enabled"
            ),
            "rbf_enabled": st.column_config.CheckboxColumn(
                "RBF-DRT enabled",
                help="True if RBF-DRT was computed"
            ),
        },
        disabled=True,
        hide_index=False,
        width="stretch"
    )
if drt_selected:
    if not drt_show_params:
        st.subheader("DRT")

    for p, data in drt_data.items():
        if data:
            if drt_3d:
                st.plotly_chart(drt_3d_plotly(data, p), width="stretch")
            else:
                st.plotly_chart(drt_plotly(data, p), width="stretch")       

# CNLS section
df_cnls = None
if analyze_cnls:
    st.subheader("CNLS")

    if cnls_rows:
        df_cnls = pd.DataFrame(cnls_rows).set_index("File")
        if len(df_cnls) > 1:
            _r_idx_set = sorted(
                {int(k[1:]) for k in df_cnls.columns if k.startswith("R") and k != "R_ohmic"}
            )
            plotable_columns = ["ASR", "R_ohmic"]
            for _i in _r_idx_set:
                for _pfx in ("R", "tau", "alpha"):
                    _col = f"{_pfx}{_i}"
                    if _col in df_cnls.columns:
                        plotable_columns.append(_col)

            # Update selectable list dynamically
            if "Line plots" in cnls_plot_modes:
                cnls_line_selection = st.multiselect(
                    "Select parameters to plot",
                    plotable_columns,
                    default=plotable_columns
                )

        # ---- Dynamic column ordering ----
        r_indices = sorted(
            {int(k[1:]) for k in df_cnls.columns if k.startswith("R") and k != "R_ohmic"}
        )

        ordered_cols = ["ASR", "R_ohmic"]

        for idx in r_indices:
            if f"R{idx}" in df_cnls.columns:
                ordered_cols.append(f"R{idx}")
            if f"tau{idx}" in df_cnls.columns:
                ordered_cols.append(f"tau{idx}")
            if f"alpha{idx}" in df_cnls.columns:
                ordered_cols.append(f"alpha{idx}")

        df_display = df_cnls[ordered_cols]

        # ---- Rename columns with Greek letters ----
        rename_map = {"R_ohmic": "Rₒₕₘ"}

        for idx in r_indices:
            if f"tau{idx}" in df_display.columns:
                rename_map[f"tau{idx}"] = f"τ{idx}"
            if f"alpha{idx}" in df_display.columns:
                rename_map[f"alpha{idx}"] = f"α{idx}"

        df_display = df_display.rename(columns=rename_map)

        if cnls_show_params:
            df_display.index = np.arange(1, len(df_display) + 1)
            df_display.index.name = "Index"
            st.dataframe(df_display, width="stretch")


        # ---- Plot section unchanged ----
        if len(df_cnls) == 1:

            series = df_cnls.iloc[0]
            cnls_file = sibling_file(files_to_process[0], "CNLS")

            if "Bar plot" in cnls_plot_modes:
                st.plotly_chart(cnls_bar_plotly(series), width="stretch")

            if "Elements fitting" in cnls_plot_modes:

                cnls_file = sibling_file(files_to_process[0], "CNLS")

                # DRT elements (already done)
                fig_elem = cnls_elements_fitting_plotly(cnls_file, df_cnls.index[0])
                if fig_elem:
                    st.plotly_chart(fig_elem, width="stretch")

                # Nyquist fit
                fig_nyq = cnls_nyquist_fit_plotly(cnls_file, df_cnls.index[0])
                if fig_nyq:
                    st.plotly_chart(fig_nyq, width="stretch")

                # Residuals
                fig_res = cnls_residuals_plotly(cnls_file, df_cnls.index[0])
                if fig_res:
                    st.plotly_chart(fig_res, width="stretch")
        else:

            if "Heatmap" in cnls_plot_modes:
                for fig in cnls_heatmap_plotly(df_cnls, st.session_state.palette_choice, cnls_heatmap_params):
                    st.plotly_chart(fig, width="stretch")

            if "Line plots" in cnls_plot_modes and cnls_line_selection:
                for param in cnls_line_selection:
                    st.plotly_chart(
                        cnls_line_plotly(df_cnls, param),
                        width="stretch"
                    )

        # ---- CNLS compare ----
        if "CNLS compare" in cnls_plot_modes:
            st.subheader("CNLS compare")

            compare_candidates = [f for f in files_to_process if sibling_file(f, "CNLS").exists()]

            if not compare_candidates:
                st.info("No CNLS files found for the selected EIS files.")
                st.session_state["cnls_compare_eis_files"] = []
            else:
                compare_label_map = {display_name_map[f.name]: f for f in compare_candidates}

                if len(compare_candidates) == 1:
                    selected_labels = list(compare_label_map.keys())
                else:
                    selected_labels = st.multiselect(
                        "Select files",
                        list(compare_label_map.keys()),
                        default=list(compare_label_map.keys()),
                        key="cnls_compare_files"
                    )

                selected_eis_files = [compare_label_map[lbl] for lbl in selected_labels]
                st.session_state["cnls_compare_eis_files"] = selected_eis_files

                for eis_file in selected_eis_files:
                    compare_cnls_file = sibling_file(eis_file, "CNLS")
                    compare_fname = display_name_map[eis_file.name]

                    fig_im = cnls_elements_im_bode_plotly(compare_cnls_file, compare_fname)
                    if fig_im:
                        st.plotly_chart(fig_im, width="stretch")

                    fig_nyq = cnls_nyquist_fit_plotly(compare_cnls_file, compare_fname)
                    if fig_nyq:
                        st.plotly_chart(fig_nyq, width="stretch")

                    fig_drt = cnls_elements_fitting_plotly(compare_cnls_file, compare_fname)
                    if fig_drt:
                        st.plotly_chart(fig_drt, width="stretch")

    else:
        st.info("CNLS enabled, but no CNLS files/sheets were found for the selected EIS files.")


# ===============================
# ZIP Export (ONLY plots shown; PNGs; non-empty)
# ===============================
if save_zip:
    export_folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    zip_path = export_folder / f"SOCEIS_figures_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Nyquist
        for p, data in nyquist_data.items():
            if not data:
                continue

            if nyquist_3d:
                if p == "DRT Fit":
                    add_nyquist_fit_3d_png(zf, data, title="DRT_Fit")
                else:
                    add_nyquist_3d_png(zf, data, p)
            else:
                if p == "DRT Fit":
                    add_nyquist_fit_png(zf, data)
                else:
                    add_nyquist_png(zf, data, p)

        if nyquist_compare_selected:
            for mode in nyquist_compare_selected:
                add_nyquist_compare_png(
                    zf,
                    mode,
                    files_to_process,
                    display_name_map
                )

        # Bode
        for p, data in bode_data.items():
            if data:
                add_bode_png(zf, data, p, real=True) # Z'
                add_bode_png(zf, data, p, real=False) # -Z"

        # DRT
        for p, data in drt_data.items():
            if data:
                if drt_3d:
                    add_drt_3d_png(zf, data, p)
                else:
                    add_drt_png(zf, data, p)


        # CNLS
        if analyze_cnls and df_cnls is not None and not df_cnls.empty:

            if len(files_to_process) == 1:

                cnls_file = sibling_file(files_to_process[0], "CNLS")

                if "Bar plot" in cnls_plot_modes:
                    add_cnls_bar_png(zf, df_cnls.iloc[0], df_cnls.index[0])

                if "Elements fitting" in cnls_plot_modes:
                    add_cnls_elements_fitting_png(
                        zf,
                        cnls_file,
                        df_cnls.index[0]
                    )
                    add_cnls_nyquist_fit_png(
                            zf,
                            cnls_file,
                            df_cnls.index[0]
                    )
                    add_cnls_residuals_png(
                            zf,
                            cnls_file,
                            df_cnls.index[0]
                    )

            else:

                if "Heatmap" in cnls_plot_modes:
                    add_cnls_heatmap_png(
                        zf,
                        df_cnls,
                        st.session_state.palette_choice,
                        cnls_heatmap_params
                    )

                if "Line plots" in cnls_plot_modes and cnls_line_selection:
                    for param in cnls_line_selection:
                        add_cnls_line_png(zf, df_cnls, param)

            if "CNLS compare" in cnls_plot_modes:
                for eis_file in st.session_state.get("cnls_compare_eis_files", []):
                    compare_cnls_file = sibling_file(eis_file, "CNLS")
                    compare_fname = display_name_map[eis_file.name]
                    add_cnls_compare_png(zf, compare_cnls_file, compare_fname)


    st.success(f"ZIP saved at: {zip_path.resolve()}")
