# DRT Frequency-Axis Fix Design

## Goal

Prevent Tikhonov DRT exports and Bode consumers from pairing reconstructed impedance with the gamma grid, while preserving import compatibility with legacy single-frequency workbooks and warning users that those workbooks may contain ambiguous Bode frequencies.

## Scope

The change covers ordinary and non-negative Tikhonov results for every `Re`, `Im`, and `ReIm` branch, all Tikhonov Excel sheets, DRT Excel import, internal reconstructed-impedance Bode plots, CNLS reference resolution, and the GUI warning shown during file import.

Nyquist calculations, gamma values, the numerical inversion itself, and the existing RBF two-grid contract remain unchanged.

## Data contract

Each Tikhonov result branch will expose:

- `f_gamma`: frequency derived from the log-spaced relaxation-time grid; aligned with `tau` and `g`.
- `f_Z`: retained measurement/evaluation frequency; aligned with `Re`, `Im`, and `Residuals`.
- `f`: backward-compatible alias of `f_gamma` so existing gamma consumers continue to work.

The producers will copy `EIS_data['f']` into `f_Z` and retain the existing calculated DRT frequency as `f` and `f_gamma`. Arrays will be one-dimensional NumPy arrays and will not share mutable storage with the caller.

## Export format

Every Tikhonov result sheet will use the following columns:

1. `Frequency_gamma/Hz`
2. `gamma/ohm·s·cm2`
3. `Frequency_Z/Hz`
4. `Re/ohm·cm2`
5. `Im/ohm·cm2`
6. `Residuals`

Columns will be constructed with `pd.Series`, matching the existing RBF export pattern and allowing future gamma and impedance grids to have different lengths.

## Import compatibility

For new workbooks, import will restore both axes and set `f` to the gamma-axis alias.

For a legacy Tikhonov sheet containing only `Frequency/Hz`, import will:

- continue loading successfully;
- assign the legacy frequency to `f`, `f_gamma`, and the fallback `f_Z` because the real impedance axis is absent from that workbook;
- set `legacy_drt_frequency_warning = True` on the imported DRT object;
- retain a list of affected sheet names for diagnostics.

The fallback does not claim that the legacy `f_Z` is correct. It only keeps the old workbook usable. Reprocessing from the original EIS data and saving again is the only reliable repair.

## GUI warning

The GUI file-import layer will collect filenames whose DRT object reports legacy ambiguous frequency data. At the end of one import operation it will show one non-blocking warning dialog, even if an object was internally loaded more than once.

Dialog content will state that the legacy DRT workbook has only one frequency column, reconstructed-impedance Bode frequencies may be incorrect, Nyquist and gamma-DRT data are unaffected, and the recommended action is to reprocess the original EIS data and save the DRT result again.

Non-GUI callers can inspect `legacy_drt_frequency_warning` and `legacy_drt_frequency_sheets`.

## Consumer changes

- Gamma plots continue using `f_gamma` with fallback to `f`.
- Reconstructed-impedance Bode plots use `f_Z` with fallback to `f`.
- Nyquist plots remain unchanged.
- CNLS DRT-axis extraction prefers `f_gamma`; reconstructed-impedance reference selection uses `f_Z`.
- Import of new workbooks restores both axes; legacy workbooks retain the fallback behavior described above.

## Testing

Tests will be written before production changes and observed failing for the missing dual-axis behavior.

- Numerical producer tests will remove interior frequencies and assert that `f_gamma` differs from, while `f_Z` equals, the retained measured frequency for both solvers and all three branches.
- Export tests will assert the new column names and row alignment.
- Import tests will cover new dual-axis workbooks and legacy single-axis workbooks, including the compatibility flag and affected-sheet list.
- Consumer tests will verify CNLS chooses `f_Z` for impedance and `f_gamma` for DRT.
- GUI warning tests will verify one aggregated warning and the required remediation text.
- The full available test suite and a source-diff audit will run before completion.

## Cleanup

After all verification succeeds, the task-owned `.planning` directory will be deleted as explicitly requested. The pre-existing `src/GUI/config.json` modification will not be changed.
