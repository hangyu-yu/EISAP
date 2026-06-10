"""
IV Curve Viewer — Streamlit app for Zahner steady-state IV data.

Launch via:
    streamlit run IV_view.py -- --root_folder /path/to/data
Or from SOCEIS GUI: click the "IV curve" button.
"""

import os
import sys
import re
import argparse
import zipfile
import subprocess
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import colormaps
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional

# ── Suppress Streamlit email prompt ──────────────────────────────────────────
def ensure_email_prompt_disabled():
    try:
        config_path = Path.home() / ".streamlit" / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")
            if "showEmailPrompt = false" in content:
                return
            if "showEmailPrompt = true" in content:
                content = content.replace("showEmailPrompt = true", "showEmailPrompt = false")
            else:
                content += ("\n[general]\nshowEmailPrompt = false\n"
                            if "[general]" not in content else "\nshowEmailPrompt = false\n")
            config_path.write_text(content, encoding="utf-8")
        else:
            config_path.write_text("[general]\nshowEmailPrompt = false\n", encoding="utf-8")
    except Exception:
        pass

ensure_email_prompt_disabled()

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--root_folder", type=str, default="")
try:
    args, _ = parser.parse_known_args()
    parsed_path = args.root_folder
except SystemExit:
    parsed_path = ""

DEFAULT_ROOT_FOLDER = Path(parsed_path) if parsed_path else Path.cwd()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="IV Curve Viewer", layout="wide")

# ── tkinter availability (for folder picker) ──────────────────────────────────
try:
    import tkinter as tk
    from tkinter import filedialog
    TK_AVAILABLE = True
except Exception:
    tk = None
    filedialog = None
    TK_AVAILABLE = False

# ═════════════════════════════════════════════════════════════════════════════
# Color palette system — identical to SOCEIS_view.py
# ═════════════════════════════════════════════════════════════════════════════

DEFAULT_COLOR_PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#B279A2",
    "#FF9DA6", "#9D755D", "#BAB0AC", "#72B7B2", "#F2CF5B",
]

PLOTLY_SEQ = {
    "Viridis (perceptual)":          pc.sequential.Viridis,
    "Cividis (colorblind-friendly)": pc.sequential.Cividis,
    "Plasma (perceptual)":           pc.sequential.Plasma,
    "Inferno (perceptual)":          pc.sequential.Inferno,
    "Magma (perceptual)":            pc.sequential.Magma,
    "Turbo (high-contrast)":         pc.sequential.Turbo,
}

PALETTE_LIBRARY = {
    "Default":                       "SOCEIS_DEFAULT",
    "Viridis (perceptual)":          "viridis",
    "Cividis (colorblind-friendly)": "cividis",
    "Plasma (perceptual)":           "plasma",
    "Inferno (perceptual)":          "inferno",
    "Magma (perceptual)":            "magma",
    "Turbo (high-contrast)":         "turbo",
    "Matplotlib tab10":              "tab10",
    "Matplotlib tab20":              "tab20",
    "Matplotlib Set2 (pastel)":      "Set2",
    "Matplotlib Dark2":              "Dark2",
    "Matplotlib Paired":             "Paired",
}

PALETTE_PREVIEW_N = 10


def _rgb_str_to_hex(s: str) -> str:
    nums = (
        s.strip().lower()
        .replace("rgba(", "").replace("rgb(", "").replace(")", "")
        .split(",")
    )
    r, g, b = [int(float(x)) for x in nums[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"


def sample_plotly_sequential(palette_choice: str, n: int,
                              lo: float = 0.10, hi: float = 0.95) -> List[str]:
    scale = PLOTLY_SEQ[palette_choice]
    t_vals = np.linspace(lo, hi, max(n, 1))
    return [_rgb_str_to_hex(c) for c in pc.sample_colorscale(scale, t_vals)]


def sample_palette_colors(palette_choice: str, n: int) -> List[str]:
    if palette_choice == "Default":
        base = DEFAULT_COLOR_PALETTE
        if n <= len(base):
            return base[:n]
        return (base * ((n + len(base) - 1) // len(base)))[:n]
    if palette_choice in PLOTLY_SEQ:
        return sample_plotly_sequential(palette_choice, n=n, lo=0.10, hi=0.95)
    cmap_name = PALETTE_LIBRARY.get(palette_choice, "tab10")
    cmap = colormaps.get_cmap(cmap_name)
    if hasattr(cmap, "colors") and cmap.colors is not None:
        base = [mcolors.to_hex(c) for c in cmap.colors]
        if n <= len(base):
            return base[:n]
        return (base * ((n + len(base) - 1) // len(base)))[:n]
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
    if "\\" in text or "_{" in text or "^{" in text:
        if text.startswith("$") and text.endswith("$"):
            return text
        return f"${text}$"
    return text


def natural_key(s: str):
    """Natural sort key: 's2' < 's10', case-insensitive."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


# ═════════════════════════════════════════════════════════════════════════════
# Folder picker — identical to SOCEIS_view.py
# ═════════════════════════════════════════════════════════════════════════════

def _resolve_initial_dir(current_dir: Optional[str],
                          fallback_dir: Optional[Path]) -> Optional[Path]:
    for candidate in [current_dir, fallback_dir]:
        if candidate is None:
            continue
        try:
            p = Path(candidate).expanduser()
            if p.exists() and p.is_dir():
                return p
        except Exception:
            pass
    return None


def pick_folder_dialog(current_dir: Optional[str] = None,
                       fallback_dir: Optional[Path] = None) -> Optional[str]:
    initial_dir = _resolve_initial_dir(current_dir, fallback_dir)
    if sys.platform == "darwin":
        try:
            choose_expr = "choose folder with prompt \"Select folder\""
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
            return folder if folder else None
        except Exception:
            return None
    if not TK_AVAILABLE:
        return None
    root_tk = tk.Tk()
    root_tk.withdraw()
    root_tk.attributes("-topmost", True)
    ask_kwargs = {}
    if initial_dir is not None:
        ask_kwargs["initialdir"] = str(initial_dir)
    folder = filedialog.askdirectory(**ask_kwargs)
    root_tk.destroy()
    return folder if folder else None


# ═════════════════════════════════════════════════════════════════════════════
# Legend position presets
# ═════════════════════════════════════════════════════════════════════════════

LEGEND_POSITIONS = {
    "Outside right":       dict(orientation='v', x=1.02,  y=1.0,   xanchor='left',   yanchor='top'),
    "Inside top-right":    dict(orientation='v', x=0.98,  y=0.98,  xanchor='right',  yanchor='top'),
    "Inside top-left":     dict(orientation='v', x=0.02,  y=0.98,  xanchor='left',   yanchor='top'),
    "Inside bottom-right": dict(orientation='v', x=0.98,  y=0.02,  xanchor='right',  yanchor='bottom'),
    "Outside bottom":      dict(orientation='h', x=0.5,   y=-0.18, xanchor='center', yanchor='top'),
}

# ═════════════════════════════════════════════════════════════════════════════
# File detection & parsing
# ═════════════════════════════════════════════════════════════════════════════

def _is_iv_file(path):
    """Return True if the file is a Zahner steady-state IV text file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if i > 60:
                    break
                if 'current/voltage' in line.lower():
                    return True
    except Exception:
        pass
    return False


def parse_iv_file(path):
    """
    Parse a Zahner steady-state IV file.
    Returns dict: {'meta': {...}, 'potential': ndarray, 'current': ndarray}
    or None on failure.
    """
    meta = {}
    potential_list, current_list = [], []
    in_data = False
    data_started = False
    potential_idx = current_idx = delimiter = None

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                stripped = line.strip()

                if not in_data:
                    if ':' in line and stripped and not stripped[0].isdigit():
                        colon_pos = line.index(':')
                        key = line[:colon_pos].rstrip('. \t').strip()
                        val = line[colon_pos + 1:].strip()
                        if key and len(key) < 40:
                            meta[key] = val

                    if 'Potential' in stripped and 'Current' in stripped:
                        in_data = True
                        if ',' in stripped:
                            delimiter = ','
                            header_parts = [p.strip() for p in stripped.split(',')]
                        else:
                            delimiter = None
                            header_parts = stripped.split()
                        for idx, h in enumerate(header_parts):
                            hl = h.lower()
                            if 'potential' in hl and potential_idx is None:
                                potential_idx = idx
                            if 'current' in hl and current_idx is None:
                                current_idx = idx
                        continue

                else:
                    if not stripped:
                        continue
                    parts = (
                        [p.strip() for p in stripped.split(',')]
                        if delimiter == ',' else stripped.split()
                    )
                    if potential_idx is None or current_idx is None:
                        continue
                    required = max(potential_idx, current_idx) + 1
                    if len(parts) >= required:
                        try:
                            potential_list.append(float(parts[potential_idx]))
                            current_list.append(float(parts[current_idx]))
                            data_started = True
                        except ValueError:
                            if data_started:
                                break
                    elif data_started:
                        break

    except Exception as e:
        print(f"[IV_view] Error reading {path}: {e}")
        return None

    if not potential_list:
        return None

    return {
        'meta':      meta,
        'potential': np.array(potential_list),
        'current':   np.array(current_list),
    }


# ═════════════════════════════════════════════════════════════════════════════
# Figure builder
# ═════════════════════════════════════════════════════════════════════════════

def build_iv_figure(entries, display_name_map, colors,
                    legend_pos_cfg, show_legend, legend_font_size, line_width):
    """Plot current [A] vs voltage [V] for all data points, no sweep split."""
    fig = go.Figure()

    for i, (fname, data) in enumerate(entries):
        if data is None:
            continue
        color = colors[i % len(colors)]
        label = latex_label(display_name_map.get(fname, Path(fname).stem))

        fig.add_trace(go.Scatter(
            x=data['current'],
            y=data['potential'],
            mode='lines',
            name=label,
            line=dict(color=color, width=line_width),
        ))

    fig.update_layout(
        xaxis_title='Current [A]',
        yaxis_title='Voltage [V]',
        template='plotly_white',
        showlegend=show_legend,
        legend=dict(**legend_pos_cfg, font=dict(size=legend_font_size)),
        margin=dict(l=65, r=20, t=30, b=65),
        height=520,
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# Export helper — matplotlib-based, identical pattern to SOCEIS_view.py
# ═════════════════════════════════════════════════════════════════════════════

def _mpl_fig_to_bytes(mpl_fig, fmt: str) -> bytes:
    buf = BytesIO()
    if fmt == "pdf":
        mpl_fig.savefig(buf, format="pdf", bbox_inches="tight", pad_inches=0.2)
    else:
        mpl_fig.savefig(buf, format=fmt, bbox_inches="tight", dpi=300)
    return buf.getvalue()


def _build_mpl_iv_figure(entries, display_name_map, colors, line_width,
                          show_legend, legend_font_size):
    """Recreate the IV figure in matplotlib for file export."""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    for i, (fname, data) in enumerate(entries):
        if data is None:
            continue
        color  = colors[i % len(colors)]
        label  = display_name_map.get(fname, Path(fname).stem)
        ax.plot(data['current'], data['potential'],
                color=color, linewidth=line_width, label=label)
    ax.set_xlabel("Current [A]", fontsize=12)
    ax.set_ylabel("Voltage [V]", fontsize=12)
    ax.grid(True, alpha=0.3)
    if show_legend:
        ax.legend(fontsize=legend_font_size)
    fig.tight_layout()
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# Streamlit UI
# ═════════════════════════════════════════════════════════════════════════════

st.title('IV Curve Viewer')

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Data folder ───────────────────────────────────────────────────────────
    if "iv_root_input" not in st.session_state:
        st.session_state.iv_root_input = str(DEFAULT_ROOT_FOLDER)

    col_left, col_right = st.columns([0.82, 0.18], vertical_alignment="bottom")
    with col_left:
        st.session_state.iv_root_input = st.text_input(
            "Data folder",
            value=st.session_state.iv_root_input,
        )
    with col_right:
        if st.button("📁", width='stretch', key="browse_data"):
            chosen = pick_folder_dialog(
                current_dir=st.session_state.iv_root_input,
                fallback_dir=DEFAULT_ROOT_FOLDER,
            )
            if chosen:
                st.session_state.iv_root_input = chosen
                st.rerun()

    root = Path(st.session_state.iv_root_input)

    # ── File discovery & selection ────────────────────────────────────────────
    # Deduplicate by lowercase name so *.txt and *.TXT don't both match the same file on Windows
    if root.is_dir():
        _seen: dict = {}
        for f in sorted(root.glob('*.txt')) + sorted(root.glob('*.TXT')):
            _seen.setdefault(f.name.lower(), f)
        candidates = list(_seen.values())
    else:
        candidates = []
    iv_files = [f for f in candidates if _is_iv_file(f)]
    iv_names   = [f.name for f in iv_files]

    # Reset selection when folder changes so stale names don't break multiselect
    if st.session_state.get("iv_last_root") != str(root):
        st.session_state.iv_selected_files = []
        st.session_state["custom_names"]    = {}
        st.session_state["iv_last_root"]    = str(root)
        # Keep the export folder following the data folder
        st.session_state.iv_export_input    = (
            str(root / "IV_figures") if root.is_dir()
            else str(DEFAULT_ROOT_FOLDER / "IV_figures")
        )

    if "iv_selected_files" not in st.session_state:
        st.session_state.iv_selected_files = []

    # Drop any leftover names that no longer exist in the current folder
    st.session_state.iv_selected_files = [
        n for n in st.session_state.iv_selected_files if n in iv_names
    ]

    sort_mode         = "Alphabetical (A → Z)"
    show_legend_table = True

    if iv_files:
        st.markdown("---")

        st.markdown("### Select IV files")
        col_l, col_r = st.columns([0.88, 0.12], vertical_alignment="bottom")
        with col_r:
            if st.button("All", width='stretch'):
                st.session_state.iv_selected_files = iv_names
                st.rerun()
        with col_l:
            st.multiselect(" ", options=iv_names, key="iv_selected_files")

        sort_mode = st.selectbox(
            "File ordering",
            ["Original selection order", "Alphabetical (A → Z)", "Alphabetical (Z → A)"],
            index=1,
        )
        show_legend_table = st.checkbox("Show personalized legend table", value=True,
                                        key="show_legend_table")

    st.markdown("---")

    # ── Color palette ─────────────────────────────────────────────────────────
    if "palette_choice" not in st.session_state:
        st.session_state.palette_choice = "Default"

    st.markdown("### Colors")
    st.selectbox("Color palette", options=list(PALETTE_LIBRARY.keys()), key="palette_choice")
    preview_colors = sample_palette_colors(st.session_state.palette_choice, n=PALETTE_PREVIEW_N)
    st.markdown(render_palette_preview(preview_colors), unsafe_allow_html=True)

    st.markdown("---")

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("### Legend")
    show_legend      = st.checkbox("Show legend on plot", value=True)
    legend_position  = st.selectbox("Position", list(LEGEND_POSITIONS.keys()), index=0,
                                    disabled=not show_legend)
    legend_font_size = st.number_input("Font size", min_value=8, max_value=28, value=12, step=1,
                                       disabled=not show_legend)
    line_width       = st.slider("Line width", min_value=1.0, max_value=5.0, value=2.0, step=0.5)

    st.markdown("---")

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("### Export")

    default_export = str(root / "IV_figures") if root.is_dir() else str(DEFAULT_ROOT_FOLDER / "IV_figures")
    if "iv_export_input" not in st.session_state:
        st.session_state.iv_export_input = default_export

    col_left, col_right = st.columns([0.82, 0.18], vertical_alignment="bottom")
    with col_left:
        st.session_state.iv_export_input = st.text_input(
            "Export folder path",
            value=st.session_state.iv_export_input,
        )
    with col_right:
        if st.button("📁", key="browse_export", width='stretch'):
            chosen = pick_folder_dialog(
                current_dir=st.session_state.iv_export_input,
                fallback_dir=root,
            )
            if chosen:
                st.session_state.iv_export_input = chosen
                st.rerun()

    export_folder = Path(st.session_state.iv_export_input)

    export_formats = st.multiselect(
        "Select formats",
        options=["png", "jpg", "pdf"],
        default=["png"],
        key="iv_export_formats",
    )
    if not export_formats:
        st.session_state.iv_export_formats = ["png"]

    save_zip = st.button("💾 Save ZIP")

# ── Guard: folder must exist ──────────────────────────────────────────────────
if not root.is_dir():
    st.warning(f'Folder not found: {root}')
    st.stop()

if not iv_files:
    st.info('No Zahner steady-state IV files (.txt) found in the selected folder.')
    st.stop()

# ── File ordering ─────────────────────────────────────────────────────────────
selected_names = list(st.session_state.get("iv_selected_files", []))
if sort_mode == "Alphabetical (A → Z)":
    selected_names = sorted(selected_names, key=natural_key)
elif sort_mode == "Alphabetical (Z → A)":
    selected_names = sorted(selected_names, key=natural_key, reverse=True)

iv_file_map       = {f.name: f for f in iv_files}
files_to_process  = [iv_file_map[n] for n in selected_names if n in iv_file_map]

if not files_to_process:
    st.info('Select at least one file from the sidebar.')
    st.stop()

# ── Custom names (session state) ──────────────────────────────────────────────
if "custom_names" not in st.session_state:
    st.session_state["custom_names"] = {}
for f in files_to_process:
    st.session_state["custom_names"].setdefault(f.name, f.name)

# ── Colors ────────────────────────────────────────────────────────────────────
n_files       = max(2, len(files_to_process))
COLOR_PALETTE = sample_palette_colors(st.session_state.palette_choice, n=n_files)

# ── display_name_map ──────────────────────────────────────────────────────────
if show_legend_table:
    display_name_map = {
        f.name: st.session_state["custom_names"].get(f.name, f.name)
        for f in files_to_process
    }
else:
    display_name_map = {f.name: f.name for f in files_to_process}

# ── Legend label editor ───────────────────────────────────────────────────────
if show_legend_table:
    st.subheader("Selected Files")

    rows = [
        {
            "Index": idx,
            "File name": f.name,
            "Personalized name (LaTeX-friendly)":
                st.session_state.custom_names.get(f.name, f.name),
        }
        for idx, f in enumerate(files_to_process, start=1)
    ]
    df_labels = pd.DataFrame(rows)

    with st.form("legend_editor_form", clear_on_submit=False):
        edited_df = st.data_editor(
            df_labels,
            key="legend_editor",
            column_config={
                "Index":     st.column_config.NumberColumn(disabled=True),
                "File name": st.column_config.TextColumn(disabled=True),
                "Personalized name (LaTeX-friendly)": st.column_config.TextColumn(),
            },
            hide_index=True,
            width='stretch',
        )
        colA, colB = st.columns([0.25, 0.75])
        with colA:
            apply_labels = st.form_submit_button("✅ Apply labels")
        with colB:
            reset_labels = st.form_submit_button("↩ Reset to filenames")

    if apply_labels:
        for _, row in edited_df.iterrows():
            st.session_state.custom_names[row["File name"]] = \
                row["Personalized name (LaTeX-friendly)"]
        st.rerun()

    if reset_labels:
        for f in files_to_process:
            st.session_state.custom_names[f.name] = f.name
        st.rerun()

# ── Parse ─────────────────────────────────────────────────────────────────────
entries = [(f.name, parse_iv_file(f)) for f in files_to_process]
valid   = [(n, d) for n, d in entries if d is not None]

if not valid:
    st.error('Could not parse any of the selected files.')
    st.stop()

# ── Main plot ─────────────────────────────────────────────────────────────────
fig = build_iv_figure(
    valid,
    display_name_map,
    COLOR_PALETTE,
    LEGEND_POSITIONS[legend_position],
    show_legend,
    int(legend_font_size),
    line_width,
)
st.plotly_chart(fig, use_container_width=True)

# ── File metadata ─────────────────────────────────────────────────────────────
with st.expander('File metadata'):
    meta_rows = []
    for fname, data in valid:
        if data:
            row = {'File': fname}
            row.update(data['meta'])
            meta_rows.append(row)
    if meta_rows:
        st.dataframe(pd.DataFrame(meta_rows).set_index('File'))

# ── Raw data preview ──────────────────────────────────────────────────────────
with st.expander('Raw data preview'):
    for fname, data in valid:
        if data is None:
            continue
        df = pd.DataFrame({'Potential_V': data['potential'], 'Current_A': data['current']})
        st.caption(fname)
        st.dataframe(df.head(200))

# ═════════════════════════════════════════════════════════════════════════════
# ZIP Export — same logic as SOCEIS_view.py
# ═════════════════════════════════════════════════════════════════════════════
if save_zip:
    try:
        export_folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_path  = export_folder / f"IV_figures_{timestamp}.zip"

        mpl_fig = _build_mpl_iv_figure(
            valid, display_name_map, COLOR_PALETTE,
            line_width, show_legend, int(legend_font_size),
        )

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fmt in export_formats:
                zf.writestr(f"IV_curve.{fmt}", _mpl_fig_to_bytes(mpl_fig, fmt))
        plt.close(mpl_fig)

        st.success(f"ZIP saved at: {zip_path.resolve()}")

    except Exception as e:
        st.error(f"Export failed: {e}")
