<p align="center">
  <img src="assets/icons/app_icon.png" alt="SOCEIS Logo" width="150"/>
</p>
<p align="center">
  <img src="assets/images/EPFL.png" alt="EPFL" height="70" hspace="20"/>
  <img src="assets/images/GEM.png" alt="GEM" height="70" hspace="20"/>
  <img src="assets/images/HydroQuebec.png" alt="Hydro-Québec" height="70" hspace="20"/>
  <img src="assets/images/BFH.png" alt="BFH" height="70" hspace="20"/>
</p>

# SOCEIS - Electrochemical Impedance Spectroscopy Analysis Suite
SOCEIS is under active development (beta stage).

## Overview
**SOCEIS** is a Python desktop application for electrochemical impedance spectroscopy workflows, integrating:

1. **EIS preprocessing and validation** (cutting, significance/outlier filtering, KK validation, optional Z-HIT)
2. **DRT analysis** (regularized inversion and lambda-related tools)
3. **CNLS / equivalent-circuit fitting** (interactive model setup and constrained fitting)

The GUI is implemented with **DearPyGui** and organized into dedicated tabs for SOCEIS home, EIS, DRT, and CNLS analysis.

## What This Repository Contains
- `SOCEIS.py`: startup script that checks dependencies and launches the GUI (`src.GUI.gui_main`)
- `src/GUI/`: user interface, tab layouts, callbacks, plotting, and table rendering
- `src/Methods/DRT/` and `src/Methods/CNLS/`: core analysis algorithms and fitting logic
- `src/Functions/01_Data_read/`: instrument/file reader implementations
- `assets/`: icons, fonts, and screenshots used by the application

## Key Capabilities
This section maps the current implemented features to scientific/technical references.

### 1. Data import and instrument adaptation
- Multi-format file ingestion for BioLogic, Gamry, Zahner, and generic text/CSV readers in `src/Functions/01_Data_read/`.
- Unified conversion to internal impedance arrays (`f`, `Re`, `Im`, `Z`) and sample-area normalization for consistent downstream analysis.
- Related references: [R1], [R2]

### 2. EIS preprocessing workflow (EIS tab)
- Upper/lower frequency cutting, low-significance filtering, optional outlier removal, and manual point removal are integrated in the `process_data` pipeline.
- The preprocessing sequence is designed to improve data consistency before model-based validation/fitting.
- Related references: [R1], [R3]

### 3. Kramers-Kronig (KK) consistency validation
- Linear/nonlinear KK-related testing and residual-based point rejection are used to evaluate physical consistency of spectra.
- KK-derived residual views and fitted-vs-measured overlays are available in plotting tabs.
- Related references: [R4], [R5]

### 4. Z-HIT modulus/phase validation
- Optional Z-HIT processing is exposed in the EIS parameter tab (`ZHIT`) and plotted against measured/KK results.
- Residual and smooth-comparison views support practical quality control of low-frequency behavior.
- Related references: [R1], [R6]

### 5. DRT inversion (Tikhonov and RBF workflows)
- DRT analysis includes Tikhonov-style regularization controls and an RBF-DRT route in the DRT tab.
- Regularization/lambda handling is integrated with single-file and batch plotting.
- Related references: [R7], [R8]

### 6. CNLS equivalent-circuit fitting
- CNLS supports interactive element configuration, parameter bounds, and constrained optimization against selected data domains.
- The workflow combines circuit definition, parameter initialization, fit execution, and single/all visualization.
- Related references: [R9], [R10], [R11]

### 7. Single vs all-file comparative analysis
- All major modules (EIS, DRT, CNLS) provide `Single` and `All` views to compare one file or many selected files in the same project.
- This supports trend analysis for degradation and operating-condition studies.
- Related references: [R1], [R2]

### 8. Batch-oriented project management
- Folder-oriented persistence for EIS/DRT/CNLS outputs, startup reloading, and backup-oriented operations are implemented for long campaigns.
- This design targets practical lab/industrial pipelines with repeated measurements.
- Related references: [R1], [R2]

## Supported Input Formats
Current readers in `src/Functions/01_Data_read/` include:

- BioLogic: `.mpt`
- Gamry: `.dta`
- Zahner: `.txt`, `.csv` (including multichannel variants)
- General text/CSV readers for standardized frequency-Re/Im formats

## Quick Start
### Requirements
- Python 3.8+ (64-bit recommended)

### Run
```bash
python SOCEIS.py
```

The launcher will attempt to install missing dependencies from `src/GUI/requirements.txt` automatically.

### Main dependencies (from current requirements)
- `numpy==2.2.6`
- `scipy`
- `pandas`
- `matplotlib`
- `dearpygui`
- `openpyxl`
- `natsort`
- `requests`
- `streamlit`
- `plotly`
- `psutil`
- `cvxopt`

## Method References
- [R1] Orazem, M. E., and Tribollet, B. *Electrochemical Impedance Spectroscopy*. 2nd ed., Wiley, 2017.
- [R2] Lasia, A. *Electrochemical Impedance Spectroscopy and its Applications*. Springer, 2014.
- [R3] Savitzky, A., and Golay, M. J. E. "Smoothing and Differentiation of Data by Simplified Least Squares Procedures." *Analytical Chemistry* 36 (1964): 1627-1639.
- [R4] Boukamp, B. A. "A Linear Kronig-Kramers Transform Test for Immittance Data Validation." *Journal of The Electrochemical Society* 142 (1995): 1885-1894.
- [R5] Schoenleber, M., Klotz, D., and Ivers-Tiffee, E. "A Method for Improving the Robustness of Linear Kramers-Kronig Validity Tests." *Electrochimica Acta* 131 (2014): 20-27.
- [R6] Ehm, W., Goehr, H., Kaus, R., Schiller, C. A., and Strunz, W. "New Methods for Automatic Impedance Spectra Evaluation." *Electrochimica Acta* 46 (2000): 145-154.
- [R7] Tikhonov, A. N., and Arsenin, V. Y. *Solutions of Ill-posed Problems*. Winston, 1977.
- [R8] Saccoccio, M., Han, X., Chen, C., and Ciucci, F. "Optimal Regularization in Distribution of Relaxation Times Applied to Electrochemical Impedance Spectroscopy." *Electrochimica Acta* 147 (2014): 470-482.
- [R9] Levenberg, K. "A Method for the Solution of Certain Non-Linear Problems in Least Squares." *Quarterly of Applied Mathematics* 2 (1944): 164-168.
- [R10] Marquardt, D. W. "An Algorithm for Least-Squares Estimation of Nonlinear Parameters." *SIAM Journal on Applied Mathematics* 11 (1963): 431-441.
- [R11] Boukamp, B. A. "A Nonlinear Least Squares Fit Procedure for Analysis of Immittance Data of Electrochemical Systems." *Solid State Ionics* 20 (1986): 31-44.

<p align="center">
  <img src="assets/images/Fig_example_main.png" width="width: 100%;">
  <img src="assets/images/Fig_example_EIS.png" width="width: 100%;">
  <img src="assets/images/Fig_example_DRT.png" width="width: 100%;">
  <img src="assets/images/Fig_example_CNLS.png" width="width: 100%;">
</p>

# Citing SOCEIS

If you use **SOCEIS** in your work, please cite our papers:

> **Caliandro, P., Nakajo, A., Diethelm, S., & Van herle, J.** (2019).  
> *Model-assisted identification of solid oxide cell elementary processes by electrochemical impedance spectroscopy measurements.*  
> Journal of Power Sources, **436**, 226838.

> **Yu, H., Frantz, C., Savioz, L., Aubin, P., Fronterotta, D., Geipel, C., Moussaoui, H., Jeanmonod, G., Wang, L., & Van herle, J.** (2025).  
> *Poisoning and recovery behavior of Ni-GDC based electrolyte-supported solid oxide fuel cell exposed to common sulfur compounds under processed biogas environment.*  
> Journal of Power Sources, **642**, 236901.

---

## You can use the BibTeX

```bibtex
@article{caliandroModelassistedIdentificationSolid2019,
  title = {Model-Assisted Identification of Solid Oxide Cell Elementary Processes by Electrochemical Impedance Spectroscopy Measurements},
  author = {Caliandro, P. and Nakajo, A. and Diethelm, S. and {Van herle}, J.},
  year = {2019},
  month = oct,
  journal = {Journal of Power Sources},
  volume = {436},
  pages = {226838},
  issn = {0378-7753},
  doi = {10.1016/j.jpowsour.2019.226838},
  urldate = {2022-06-24},
  lccn = {2}
}

@article{yuPoisoningRecoveryBehavior2025,
  title = {Poisoning and Recovery Behavior of {{Ni-GDC}} Based Electrolyte-Supported Solid Oxide Fuel Cell Exposed to Common Sulfur Compounds under Processed Biogas Environment},
  author = {Yu, Hangyu and Frantz, C{\'e}dric and Savioz, Louis and Aubin, Philippe and Fronterotta, Dante and Geipel, Christian and Moussaoui, Hamza and Jeanmonod, Guillaume and Wang, Ligang and {Van herle}, Jan},
  year = {2025},
  month = jun,
  journal = {Journal of Power Sources},
  volume = {642},
  pages = {236901},
  issn = {0378-7753},
  doi = {10.1016/j.jpowsour.2025.236901},
  urldate = {2025-04-13},
  lccn = {3}
}
```

# Major updates
## ---------- Date: 2025.05.07 ----------
Beta version 0.2 with complete EIS, DRT and CNLS fit functionalities. Small bugs to be fixed
### To do list
- [ ] If CNLS fit results are not completely saved, error.
- [ ] Pop-up window to indicate the fault operation
- [ ] Simply the batch process name with ID+number-file_name
- [ ] Pop-up progress bar for the saving, processing
- [ ] Modularized code design
- [ ] Delete only the curves instead of the whole tab
- [ ] Add functions
	- [ ] Add Frequency-Tau switch for CNLS fit
	- [ ] Add Error bar for CNLS fit in long-term durability data
	- [ ] Add Warburg element for Li-BAT
  - [ ] Peak finder for quick frequency selection
  - [ ] Plot lambda in DRT
  - [ ] Plot ohmic resistance and polarization resistance trend in EIS and DRT tabs
	- [ ] Interactive manual selected points for CNLS fit frequency determine
	- [ ] Visualized equivalent circuit model assembly and usage of only basic circuit component R, C, L, Q, fFLW, FLW, G, etc.
	- [ ] Z-HIT smoothing from Zahner
	- [ ] Different DRT methodologies
	- [ ] Image save
## ---------- Date: 2025.02.12 ----------
### To do list
- [x] Translate all the codes in Matlab environment into python code
	- [x] Check the results between the matlab environment and python environment 
- [x] Define the best HMI tool in python with open-access
