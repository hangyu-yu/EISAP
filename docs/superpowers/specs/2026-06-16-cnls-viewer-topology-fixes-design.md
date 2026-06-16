# CNLS Viewer — Custom-Topology Fixes (Design)

Date: 2026-06-16
File touched: `src/Functions/SOCEIS_view.py` (Streamlit viewer, run via `streamlit run`)
Reference data: `D:\Downloads\Stack` (EIS/DRT/CNLS sibling folders)

## Problem

After custom topology was added to CNLS fitting, the viewer still parses circuits
with hardcoded `re.findall(r"RQ\d+", …)` and fixed `Z`-sheet column offsets. As a
result, standalone elements (e.g. extra `R8`, inductors `L1`/`L9`) are silently
dropped from every CNLS plot.

CNLS data layout (per file, e.g. `EIS_Day1_0.xlsx`):
- `Summary` sheet: `ElementsNames` (`['L1','R2','RQ3'…'RQ7','R8','L9']`),
  `ElementsType` (`['Inductor','Resistor','RQ',…,'Resistor','Inductor']`),
  `topology` (`L1 + R2 + RQ3 + … + RQ7 //( R8 + L9)`).
- `Z` sheet: total/measured/residual columns plus per-element `<name>_Re`/`<name>_Im`.
- `DRT` sheet: `f`, `DRTmes`, `DRT`, then per-element `DRT<name>` columns.
- `Elements` sheet (`CNLS_SHEET`): `ElementsParamNames` / `ElementsParamValues`
  (`L1_L`, `R2_R`, `RQ3_R`, `RQ3_tau0`, `RQ3_alpha`, …, `R8_R`, `L9_L`).

## Three issues

1. CNLS value plots and CNLS-compare plots do not draw standalone R / L.
   Also: add manual X/Y limit inputs for CNLS compare.
2. CNLS section does not draw the equivalent circuit model (ECM).
3. Nyquist compare lacks a "CNLS Fit vs Truncated" option.

## Design

### Shared foundation — generic element mapping
New helper that, given a CNLS `pd.ExcelFile`, returns an ordered list of elements
`{name, type, z_re_col, z_im_col, drt_col}` resolved by **header name** from the
`Z`/`DRT` sheets (element order from `Summary.ElementsNames`). Element class from
`Summary.ElementsType`. This replaces every fixed-offset / RQ-only assumption.

### Issue 1 — value plots + CNLS compare
- `extract_cnls_parameters` extracts every element from the `Elements` sheet:
  - lowest-index Resistor → `R_ohmic`; lowest-index Inductor → `L_hf`.
  - every other resistance (RQ resistances and standalone `R8`) → `R{idx}`,
    so it flows into `R_pol` and `ASR` automatically.
    Accounting target: `R_pol` = whole circuit except `L1` (HF inductance) and
    `R2` (ohmic). `ASR = R_ohmic + R_pol`.
  - other inductors → `L{idx}`, plotted as their own series, never in R sums.
- Line / Heatmap / Bar plottable-column builders gain the `L_hf` / `L{idx}`
  columns (`R{idx}` already flows in).
- `cnls_nyquist_fit_plotly`, `cnls_elements_im_bode_plotly`,
  `cnls_elements_fitting_plotly` iterate **all** elements via the shared mapping.
  Nyquist arcs keep the cumulative-real-offset stacking, with the inductor offset
  rule ported from the dearpygui `update_single_plots` element view.
- New "CNLS compare axis limits" expander (X min/max, Y min/max; blank = auto),
  applied to the three CNLS-compare figures.

### Issue 2 — ECM schematic (real symbols)
Embed a self-contained copy of `parse_topology` (series/parallel/leaf AST) so the
viewer stays standalone. Recursive matplotlib renderer: series = horizontal chain,
parallel = vertical branches with split/merge nodes. Symbols by element type:
resistor zig-zag, inductor coil, capacitor plates, RQ/CPE box (fallback: labeled
box). Rendered with `st.pyplot` in the single-file CNLS section and added to ZIP
export.

### Issue 3 — Nyquist compare
Add mode `"CNLS Fit vs Truncated"`: load the CNLS sibling `Z` sheet, plot
`Ztot_Re`/`Ztot_Im` (cols 3/4) as a line vs truncated measured points — same
pattern as existing "X vs Truncated" modes, in both interactive figure and PNG
export. Mode is offered only when CNLS files exist.

## Out of scope
The dearpygui GUI (`src/GUI/…`) is unchanged. No refactor beyond what these fixes
require.
