# DRT Frequency-Axis Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store and consume separate gamma and reconstructed-impedance frequency axes for Tikhonov DRT, while importing legacy workbooks with one aggregated GUI warning.

**Architecture:** Both Tikhonov solvers return an explicit `f_gamma` and `f_Z`, retaining `f` as a legacy gamma alias. Small serialization helpers in `DRT.py` centralize the repeated Excel contract, consumers select the axis matching their values, and `file_list.py` aggregates legacy-import warnings at the GUI boundary.

**Tech Stack:** Python 3, NumPy, SciPy, pandas, openpyxl, Dear PyGui, pytest.

**Spec:** `docs/superpowers/specs/2026-09-29-drt-frequency-axis-fix-design.md`

## Global Constraints

- Preserve the pre-existing `src/GUI/config.json` change.
- Do not change the DRT numerical inversion, gamma values, or Nyquist behavior.
- New workbooks use `Frequency_gamma/Hz` and `Frequency_Z/Hz`; legacy `Frequency/Hz` workbooks remain importable.
- A legacy workbook produces one warning per GUI import operation, not one warning per sheet or internal object load.
- Delete `.planning` only after fresh verification passes.

## Review Focus

- Interior frequency removals: producer tests assert `f_Z` retains gaps while `f_gamma` is log-uniform.
- Solver parity: parameterized tests cover ordinary and non-negative Tikhonov.
- Branch parity: parameterized tests cover `Re`, `Im`, and `ReIm`.
- Legacy ambiguity: import tests assert successful fallback plus warning state, without claiming the fallback `f_Z` is accurate.
- Duplicate GUI loads: warning aggregation tests pass duplicate filenames and assert one normalized message entry.

---

### Task 1: Tikhonov dual-axis producer contract

**Files:**

- Create: `tests/test_drt_frequency_axes.py`
- Modify: `src/Methods/DRT/Utils/DRT_tikhonov.py:37-114`
- Modify: `src/Methods/DRT/Utils/DRT_tknv_pos.py:35-122`

**Interfaces:**

- Consumes: EIS mappings containing `f`, `Re`, `Im`, `omega`, and `tau`.
- Produces: every solver branch exposes `f`, `f_gamma`, and `f_Z` NumPy arrays; `f` equals `f_gamma` for compatibility.

- [ ] **Step 1: Write failing producer regression tests**

Create a hand-controlled log-spaced frequency array, delete interior indices, run each real solver, and assert for each branch:

```python
np.testing.assert_allclose(result[branch]["f_Z"], retained_f)
np.testing.assert_allclose(result[branch]["f"], result[branch]["f_gamma"])
assert not np.allclose(result[branch]["f_gamma"], retained_f)
```

Also mutate the input frequency after the call and assert `f_Z` did not change, proving the result owns its axis array.

- [ ] **Step 2: Run tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: FAIL with missing `f_gamma` or `f_Z`, demonstrating the old ambiguous contract.

- [ ] **Step 3: Implement the minimal producer fields**

In both solvers, create `f_gamma` from the existing calculated `f`, create `f_Z = np.asarray(EIS_data['f'], dtype=float).reshape(-1).copy()`, and add both keys to `Re`, `Im`, and `ReIm`. Retain `'f': f_gamma`.

- [ ] **Step 4: Run producer tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: all producer cases PASS.

### Task 2: Tikhonov Excel serialization and legacy parsing

**Files:**

- Extend: `tests/test_drt_frequency_axes.py`
- Modify: `src/Methods/DRT/DRT.py:24-30, 1071-1250, 1497-1625`

**Interfaces:**

- Produces `_tknv_export_frame(mode_data) -> pd.DataFrame` with the six-column new schema.
- Produces `_parse_tknv_sheet(data) -> tuple[dict, bool]`, where the Boolean reports legacy single-axis input.
- `DRT.import_data_DRT()` exposes `legacy_drt_frequency_warning: bool` and `legacy_drt_frequency_sheets: list[str]`.

- [ ] **Step 1: Write failing serialization tests**

Test the real helper interface desired by the spec using unequal axis lengths:

```python
frame = _tknv_export_frame(mode_data)
assert frame.columns.tolist() == [
    "Frequency_gamma/Hz", "gamma/ohm·s·cm2", "Frequency_Z/Hz",
    "Re/ohm·cm2", "Im/ohm·cm2", "Residuals",
]
assert frame["Frequency_Z/Hz"].dropna().tolist() == [1000.0, 10.0, 1.0]
```

Test `_parse_tknv_sheet()` with a new dual-axis frame and a literal legacy frame. Assert the new frame restores both axes without a warning and the legacy frame loads, sets both fallback axes to `Frequency/Hz`, and returns `True`.

- [ ] **Step 2: Run serialization tests and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: collection/import failure because the helpers do not exist.

- [ ] **Step 3: Implement minimal helpers and route all Tikhonov sheets through them**

Add the two module-level helpers. Replace every repeated Tikhonov DataFrame construction with `_tknv_export_frame(...)`. In import, use `_parse_tknv_sheet`, reset legacy warning state at the start of each workbook import, and record each affected sheet once.

- [ ] **Step 4: Run serialization tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: producer and serialization/import cases PASS.

### Task 3: Correct internal and CNLS consumers

**Files:**

- Extend: `tests/test_drt_frequency_axes.py`
- Modify: `src/Methods/DRT/DRT.py:712-812`
- Modify: `src/Methods/CNLS/Utils/DataReference.py:38-210`

**Interfaces:**

- Gamma consumers resolve `f_gamma`, then legacy `f`.
- Impedance consumers resolve `f_Z`, then legacy `f`.
- `resolve_cnls_reference()` returns `drt_f` from the gamma axis and `z_f` from the impedance axis.

- [ ] **Step 1: Write failing CNLS consumer tests**

Create an EIS-like object whose Tikhonov `ReIm` branch has deliberately different literal `f_gamma` and `f_Z`. Assert `resolve_cnls_reference(..., 'smooth_DRT')` returns the former as `drt_f` and the latter as `z_f`.

- [ ] **Step 2: Run consumer test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: FAIL because the current smooth-DRT impedance path uses legacy `f`.

- [ ] **Step 3: Update consumers minimally**

Use `f_gamma` for DRT plotting and DRT-axis extraction. Use `f_Z` for reconstructed Re/Im Bode plotting and CNLS `z_f`. Keep `.get(..., legacy_f)` fallbacks for imported legacy objects.

- [ ] **Step 4: Run consumer tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py -v`

Expected: all current tests PASS.

### Task 4: Aggregated legacy GUI warning

**Files:**

- Create: `tests/test_legacy_drt_warning.py`
- Modify: `src/GUI/Utils/file_list.py:496-680`

**Interfaces:**

- Produces `_legacy_drt_warning_message(file_names) -> str` with normalized unique filenames.
- The existing file-import operation calls `progress_modal.show_warning_dialog(title, message)` once when at least one imported object reports legacy ambiguity.

- [ ] **Step 1: Write failing warning-message test**

Pass `['a.xlsx', 'a.xlsx', 'b.xlsx']` and assert each filename occurs once, the message contains `Bode`, states Nyquist/DRT are unaffected, and recommends reprocessing and saving again.

- [ ] **Step 2: Run warning test and verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_legacy_drt_warning.py -v`

Expected: collection/import failure because the message helper does not exist.

- [ ] **Step 3: Implement warning aggregation and popup**

Add the pure message helper. During `update_file_list`, collect the logical data filenames after successful DRT imports whose object has `legacy_drt_frequency_warning`. At the end of the import operation, call `show_warning_dialog` once with the aggregated message. Do not show it for new dual-axis workbooks.

- [ ] **Step 4: Run warning and regression tests and verify GREEN**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_legacy_drt_warning.py tests/test_drt_frequency_axes.py -v`

Expected: all tests PASS.

### Task 5: Full verification and requested cleanup

**Files:**

- Verify all modified source and test files.
- Delete: `.planning/`

- [ ] **Step 1: Run the full available test suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`

Expected: zero failures. If unrelated pre-existing failures appear, report them by name and do not conceal them.

- [ ] **Step 2: Run syntax/import verification**

Run: `.\.venv\Scripts\python.exe -m compileall -q src tests`

Expected: exit code 0 with no output.

- [ ] **Step 3: Inspect the complete diff**

Run: `git diff --check` and `git diff -- src tests docs/superpowers`

Expected: no whitespace errors; every source line traces to the dual-axis fix or legacy warning. Confirm `src/GUI/config.json` remains the pre-existing unrelated change.

- [ ] **Step 4: Delete task planning state**

After all preceding checks pass, resolve `C:\Users\hayu\Desktop\Git\EISAP\.planning` as an absolute path, verify it is inside the EISAP workspace and is exactly the requested directory, then remove it recursively.

- [ ] **Step 5: Re-run focused tests after cleanup and report**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_drt_frequency_axes.py tests/test_legacy_drt_warning.py -v`

Expected: all focused tests PASS and `.planning` no longer exists.
